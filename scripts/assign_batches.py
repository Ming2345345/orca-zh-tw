"""把 pending/batch-*.json 平均分給多位翻譯 worker。

用法：python3 scripts/assign_batches.py [--max-workers 4] [--pending pending]
輸出 JSON：{"workers": [["pending/batch-001.json", ...], ...]}
- 批次數 ≤ 2 時只分一組（由協調者自己翻，不值得開 worker）。
- 依條目數由多到少，每次分給目前總條目最少的那組，讓每位 worker 的量接近。
"""
import argparse
import json
from pathlib import Path


def entry_count(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(data, dict):
        data = data.get('entries', data)
    return len(data)


def assign(batches, max_workers):
    """batches: [(path, 條目數)]；回傳每組的路徑清單（依檔名排序）。"""
    if not batches:
        return []
    count = 1 if len(batches) <= 2 else min(max_workers, len(batches))
    groups = [[] for _ in range(count)]
    totals = [0] * count
    for path, size in sorted(batches, key=lambda item: (-item[1], item[0])):
        index = totals.index(min(totals))
        groups[index].append(path)
        totals[index] += size
    return [sorted(group) for group in groups]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--max-workers', type=int, default=4)
    parser.add_argument('--pending', default='pending')
    args = parser.parse_args(argv)
    if args.max_workers < 1:
        parser.error('--max-workers 必須大於零')
    paths = sorted(Path(args.pending).glob('batch-*.json'))
    batches = [(str(path), entry_count(path)) for path in paths]
    print(json.dumps({'workers': assign(batches, args.max_workers)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
