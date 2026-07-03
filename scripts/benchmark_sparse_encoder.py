#!/usr/bin/env python3
"""Benchmark: compare TF-only vs full BM25 (IDF + length norm) sparse encoders.

Usage:
    uv run python scripts/benchmark_sparse_encoder.py
"""

from __future__ import annotations

import statistics
import time
from pathlib import Path

from src.core.search.sparse_encoder import (
    IDFCalculator,
    _encode_single,
    _token_id,
    _tokenize,
    bm25_idf_sparse_encoder,
    bm25_sparse_encoder,
)

DATA_DIR = Path("data/sigmaref")


def load_corpus() -> list[str]:
    """Load text files from the sigmaref directory."""
    texts: list[str] = []
    if not DATA_DIR.exists():
        print(f"[warn] {DATA_DIR} not found — using synthetic corpus")
        return _synthetic_corpus(1_000)
    for f in DATA_DIR.rglob("*.txt"):
        if f.is_file():
            texts.append(f.read_text(encoding="utf-8", errors="replace"))
    texts += [p.read_text(encoding="utf-8", errors="replace") for p in DATA_DIR.rglob("*.md")]
    print(f"Loaded {len(texts)} documents from {DATA_DIR}")
    return texts


def _synthetic_corpus(n: int) -> list[str]:
    """Generate realistic Sigma rule-like documents."""
    import random

    random.seed(42)

    titles = [
        "Suspicious Process Creation",
        "Registry Persistence via Run Keys",
        "PowerShell Encoded Command Execution",
        "Scheduled Task Creating Remote Access",
        "WMI Persistence Script Execution",
        "LSASS Memory Access via Mimikatz",
        "DNS Query to Dynamic DNS Domain",
        "Service Path Without Quotes",
        "Office Application Creating Suspicious Files",
        "Net.exe User Account Creation",
        "BITSAdmin Download to Temp",
        "Certutil URL Download",
        "CMSTP Execution",
        "DLL Side-Loading via AppInit",
        "Event Log Cleared by wevtutil",
        "Kerberoasting with RC4 Encryption",
        "Mailslot Creation for Pipe Communication",
        "Netsh Port Forwarding",
        "ODBC Driver Registration",
        "Print Spooler Adding Printer Driver",
    ]
    fields = [
        "Image",
        "CommandLine",
        "ParentImage",
        "TargetObject",
        "Details",
        "PipeName",
        "ServiceFileName",
        "RegistryKey",
        "Payload",
        "QueryName",
        "DstIp",
        "SrcIp",
    ]
    values = [
        r"*.exe",
        r"*.dll",
        r"*.ps1",
        r"*.vbs",
        r"*.js",
        r"powershell.exe -enc *",
        r"cmd.exe /c *",
        r"reg.exe add *",
        r"schtasks.exe /create *",
        r"wmic.exe *",
        r"net.exe user *",
        r"certutil.exe -urlcache *",
        r"%temp%\\*",
        r"%appdata%\\*",
        "SYSTEM\\CurrentControlSet\\Services\\*",
        "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run\\*",
    ]
    logsource_categories = [
        "process_creation",
        "registry_set",
        "file_event",
        "network_connection",
        "wmi_event",
        "dns_query",
        "windows_sysmon",
        "security_audit",
    ]
    products = ["windows", "linux", "macos"]
    statuses = ["stable", "test", "experimental", "deprecated"]
    levels = ["high", "medium", "low", "critical"]
    tags_pool = [
        "attack.execution",
        "attack.persistence",
        "attack.defense_evasion",
        "attack.credential_access",
        "attack.discovery",
        "attack.lateral_movement",
        "attack.collection",
        "attack.command_and_control",
        "attack.t1059.001",
        "attack.t1547.001",
        "attack.t1003.001",
        "attack.t1053.005",
        "attack.t1047",
        "attack.t1087.002",
    ]

    docs: list[str] = []
    for i in range(n):
        title = random.choice(titles)
        status = random.choice(statuses)
        level = random.choice(levels)
        product = random.choice(products)
        category = random.choice(logsource_categories)
        field = random.choice(fields)
        value = random.choice(values)
        tags = " ".join(random.sample(tags_pool, random.randint(2, 4)))
        detection = f"{field} contains '{value}'"

        doc = (
            f"title: {title}\n"
            f"id: synth-{i:06d}\n"
            f"status: {status}\n"
            f"description: Detects {title.lower()} technique used by threat actors for persistence "
            f"and privilege escalation on {product} systems. Related to MITRE ATT&CK techniques.\n"
            f"author: Benchmark Generator\n"
            f"date: 2024/01/01\n"
            f"tags: {tags}\n"
            f"logsource:\n"
            f"  category: {category}\n"
            f"  product: {product}\n"
            f"detection:\n"
            f"  selection:\n"
            f"    {detection}\n"
            f"  condition: selection\n"
            f"falsepositives:\n"
            f"  - Legitimate administrative activity\n"
            f"  - Software installation\n"
            f"level: {level}\n"
            f"references:\n"
            f"  - https://attack.mitre.org/techniques/T{1000 + (i % 9000):04d}/\n"
        )
        docs.append(doc)

    return docs


def _overlap(j: list[int], k: list[int]) -> float:
    s = set(j)
    return sum(1 for x in k if x in s)


def benchmark_speed(encoder, texts: list[str], name: str) -> float:
    start = time.perf_counter()
    for _ in range(3):
        encoder(texts)
    elapsed = time.perf_counter() - start
    avg = elapsed / 3
    print(f"  {name}: {avg:.4f}s avg (3 runs, {len(texts)} docs)")
    return avg


def benchmark_quality(
    query_texts: list[str],
    corpus: list[str],
    idf_map: dict[str, float],
    avg_doc_len: float,
) -> None:
    """Compare top-10 overlap between TF-only and full BM25."""
    print("\n=== Quality comparison (top-k term overlap) ===\n")

    for q in query_texts:
        tf_indices, _ = _encode_single(q)
        bm25_indices, _ = _encode_single(q, idf_map=idf_map, avg_doc_len=avg_doc_len)
        overlap_frac = _overlap(tf_indices, bm25_indices) / max(len(tf_indices), 1)
        print(
            f"  query: {q[:60]:<60s}  "
            f"TF terms: {len(tf_indices):>3d}  "
            f"BM25 terms: {len(bm25_indices):>3d}  "
            f"overlap: {overlap_frac:.0%}"
        )


def compute_corpus_stats(
    corpus: list[str],
) -> tuple[dict[str, float], float]:
    """Compute IDF map and average document length from the corpus."""
    calc = IDFCalculator()
    total_tokens = 0
    for doc in corpus:
        total_tokens += calc.add_document(doc)
    avg_doc_len = total_tokens / max(len(corpus), 1)
    idf_map = calc.idf()
    print(f"\nCorpus: {len(corpus)} docs, {len(idf_map)} unique terms, avg len={avg_doc_len:.1f}")
    return idf_map, avg_doc_len


def main() -> None:
    corpus = load_corpus()
    idf_map, avg_doc_len = compute_corpus_stats(corpus)

    queries = [
        "process creation with image endswith exe",
        "registry modification run keys persistence",
        "network connection suspicious ip address",
        "powershell encoded command execution",
        "scheduled task lateral movement",
    ]

    # Speed benchmark
    print("\n=== Speed benchmark ===\n")
    benchmark_speed(bm25_sparse_encoder, corpus, "TF-only (1+log(tf))")
    benchmark_speed(
        lambda t: bm25_idf_sparse_encoder(t, idf_map=idf_map, avg_doc_len=avg_doc_len),
        corpus,
        "Full BM25 (IDF + length norm)",
    )

    # Quality benchmark
    benchmark_quality(queries, corpus, idf_map, avg_doc_len)

    # IDF distribution
    if idf_map:
        values = list(idf_map.values())
        print("\n=== IDF distribution ===\n")
        print(f"  min:  {min(values):.3f}")
        print(f"  max:  {max(values):.3f}")
        print(f"  mean: {statistics.mean(values):.3f}")
        print(
            f"  <1.0: {sum(1 for v in values if v < 1.0)} terms ({sum(1 for v in values if v < 1.0) / len(values):.1%})"
        )

    # Term ID collision rate
    tokens_seen = {t for doc in corpus for t in _tokenize(doc.lower()) if len(t) >= 3}
    ids = {_token_id(t) for t in tokens_seen}
    print("\n=== Token-ID collision ===\n")
    print(f"  Unique tokens: {len(tokens_seen)}")
    print(f"  Unique IDs:    {len(ids)}")
    print(f"  Collision rate: {1 - len(ids) / max(len(tokens_seen), 1):.4%}")

    # Qdrant native BM25 recommendation
    print("\n=== Recommendation ===\n")
    print("  Qdrant modifier=IDF: available via SparseVectorParams(modifier=Modifier.IDF)")
    print("  Custom IDF encoder:  implemented (use bm25_idf_sparse_encoder)")
    print("  Recommendation:      enable modifier=IDF in collection creation")
    print("                        + keep custom encoder as fallback for offline/embedding")


if __name__ == "__main__":
    main()
