"""Benchmark: flat vs rich Sigma rule chunking performance."""

import time
from pathlib import Path
from typing import Any

import pytest

from src.rag.transforms.base import TransformConfig
from src.rag.transforms.sigma.chunker import SigmaChunker
from src.rag.transforms.sigma.parser import SigmaParser


def _make_rule(title: str, i: int) -> str:
    return f"""
title: {title}
id: bench-{i:04d}
status: test
description: Benchmark rule {i} for flat vs rich chunking comparison
author: Benchmark
date: 2024/01/01
logsource:
    category: process_creation
    product: windows
detection:
    selection:
        Image|endswith: '.exe'
        CommandLine|contains: '{title.lower().replace(" ", "_")}'
    filter_main:
        EventID: 9999
    condition: selection and not filter_main
falsepositives:
    - Admin activity
    - Software installers
tags:
    - attack.t1059
    - attack.t1078
    - windows
level: high
references:
    - https://example.com/bench-{i}
"""


@pytest.fixture
def rules_dir(tmp_path: Path) -> Path:
    d = tmp_path / "bench_rules"
    d.mkdir()
    for i in range(10):
        f = d / f"rule_{i:04d}.yml"
        f.write_text(_make_rule(f"Benchmark Rule {i}", i))
    return d


class TestFlatVsRichBenchmark:
    def test_flat_produces_one_chunk_per_rule(self, rules_dir: Path) -> None:
        config = TransformConfig(enable_rich_chunks=False)
        parser = SigmaParser(config)
        all_docs: list[Any] = []

        for f in sorted(rules_dir.iterdir()):
            docs = parser.parse(f)
            all_docs.extend(parser.chunk(docs))

        assert len(all_docs) == 10

    def test_rich_produces_multiple_chunks_per_rule(self, rules_dir: Path) -> None:
        config = TransformConfig(enable_rich_chunks=True)
        chunker = SigmaChunker(config)
        all_docs: list[Any] = []

        for f in sorted(rules_dir.iterdir()):
            docs = chunker.parse(f)
            all_docs.extend(chunker.chunk(docs))

        assert len(all_docs) > 50

    def test_benchmark_flat_vs_rich(self, rules_dir: Path) -> None:
        sizes = [10, 50]

        for n_rules in sizes:
            test_dir = rules_dir
            if n_rules > 10:
                test_dir = rules_dir.parent / f"bench_{n_rules}"
                test_dir.mkdir(exist_ok=True)
                for i in range(n_rules):
                    f = test_dir / f"rule_{i:04d}.yml"
                    if not f.exists():
                        f.write_text(_make_rule(f"Benchmark Rule {i}", i))

            # Flat
            config_flat = TransformConfig(enable_rich_chunks=False)
            parser = SigmaParser(config_flat)
            start = time.perf_counter()
            flat_docs: list[Any] = []
            for f in sorted(test_dir.iterdir()):
                docs = parser.parse(f)
                flat_docs.extend(parser.chunk(docs))
            flat_time = time.perf_counter() - start
            flat_chars = sum(len(d.text) for d in flat_docs)

            # Rich
            config_rich = TransformConfig(enable_rich_chunks=True)
            chunker = SigmaChunker(config_rich)
            start = time.perf_counter()
            rich_docs: list[Any] = []
            for f in sorted(test_dir.iterdir()):
                docs = chunker.parse(f)
                rich_docs.extend(chunker.chunk(docs))
            rich_time = time.perf_counter() - start
            rich_chars = sum(len(d.text) for d in rich_docs)

            speed_ratio = rich_time / flat_time if flat_time > 0 else 0
            size_ratio = rich_chars / flat_chars if flat_chars > 0 else 0

            print(f"\n--- {n_rules} rules ---")
            print(f"  Flat:  {len(flat_docs):>4} docs, {flat_time:.3f}s, {flat_chars:>6} chars")
            print(f"  Rich:  {len(rich_docs):>4} docs, {rich_time:.3f}s, {rich_chars:>6} chars")
            print(f"  Speed: {speed_ratio:.1f}x slower (rich vs flat)")
            print(f"  Size:  {size_ratio:.1f}x more text (rich vs flat)")

            assert len(flat_docs) == n_rules
            assert len(rich_docs) > n_rules
