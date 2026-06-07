"""Benchmark: rich Sigma rule chunking performance."""

import time
from pathlib import Path
from typing import Any

import pytest

from src.core.base import TransformConfig
from src.core.sigma.chunker import SigmaChunker


def _make_rule(title: str, i: int) -> str:
    return f"""
title: {title}
id: bench-{i:04d}
status: test
description: Benchmark rule {i} for rich chunking
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


class TestRichChunkingBenchmark:
    def test_rich_produces_multiple_chunks_per_rule(self, rules_dir: Path) -> None:
        config = TransformConfig()
        chunker = SigmaChunker(config)
        all_docs: list[Any] = []

        for f in sorted(rules_dir.iterdir()):
            docs = chunker.parse(f)
            all_docs.extend(chunker.process(docs))

        assert len(all_docs) > 50

    def test_benchmark_rich(self, rules_dir: Path) -> None:
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

            config = TransformConfig()
            chunker = SigmaChunker(config)
            start = time.perf_counter()
            rich_docs: list[Any] = []
            for f in sorted(test_dir.iterdir()):
                docs = chunker.parse(f)
                rich_docs.extend(chunker.process(docs))
            rich_time = time.perf_counter() - start
            rich_chars = sum(len(d.text) for d in rich_docs)

            print(f"\n--- {n_rules} rules ---")
            print(f"  Rich:  {len(rich_docs):>4} docs, {rich_time:.3f}s, {rich_chars:>6} chars")

            assert len(rich_docs) > n_rules
