#!/usr/bin/env python3
"""Reproducible local-only recall timing on synthetic notes; no provider calls."""
import argparse
import json
from pathlib import Path
import platform
import statistics
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hae import memory, provider, recall


def benchmark(count, runs):
    with tempfile.TemporaryDirectory(prefix='hae-benchmark-') as temporary:
        root = Path(temporary).resolve()
        for folder in ['System', 'Projects', 'Sessions', 'Practices']:
            (root / folder).mkdir()
        (root / 'System/hae-config.json').write_text(json.dumps({'backend': 'local', 'recall_candidates': 12}))
        (root / 'System/hae-projects.json').write_text(json.dumps([
            {'id': 'comet', 'name': 'Comet', 'scope': 'personal', 'paths': [str(root / 'workspace')], 'note': 'Projects/Comet.md'}]))
        (root / 'Projects/Comet.md').write_text(memory.frontmatter({'project': 'comet', 'scope': 'personal'}) + '# Comet\n')
        expected = 'Sessions/checkpoint-0500.md' if count > 500 else 'Sessions/checkpoint-0000.md'
        for i in range(count):
            path = f'Sessions/checkpoint-{i:04d}.md'
            body = 'Use SQLite for comet offline drafts; verify reconnect behavior.' if path == expected else f'Component {i}: verified layout spacing and documented the review.'
            (root / path).write_text(memory.frontmatter({'project': 'comet', 'scope': 'personal', 'status': 'curated'}) + '# Checkpoint\n\n' + body + '\n')
        timings = []
        with patch.object(provider, 'evaluate', side_effect=AssertionError('Unexpected provider call')):
            for _ in range(runs + 1):
                start = time.perf_counter()
                result = recall.recall(root, 'comet', 'comet offline SQLite')
                timings.append((time.perf_counter() - start) * 1000)
                if not result['matches'] or result['matches'][0]['path'] != expected:
                    raise AssertionError('Expected memory was not ranked first')
                if any(row['path'] not in {expected, 'Projects/Comet.md'} for row in result['matches']):
                    raise AssertionError('Irrelevant metadata produced a memory match')
        warm = sorted(timings[1:])
        report = {'kind': 'synthetic local recall; not end-to-end model-session latency',
            'platform': platform.system(), 'python': platform.python_version(), 'notes': count,
            'warm_runs': runs, 'cold_ms': round(timings[0], 2), 'warm_median_ms': round(statistics.median(warm), 2),
            'warm_p95_ms': round(warm[min(len(warm)-1, int(len(warm)*0.95))], 2),
            'top_match_correct': True, 'irrelevant_matches': 0, 'provider_calls': 0, 'generative_worker_calls': 0,
            'max_excerpt_characters': 3600, 'response_characters': len(json.dumps(result))}
        return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--notes', type=int, default=1000)
    parser.add_argument('--runs', type=int, default=20)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not 1 <= args.notes <= 5000 or not 1 <= args.runs <= 100:
        parser.error('Use 1–5000 notes and 1–100 warm runs')
    report = benchmark(args.notes, args.runs)
    text = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    print(text)
