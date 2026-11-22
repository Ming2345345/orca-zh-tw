"""平行翻譯的批次分配：每個批次恰好分到一組，各組量接近。"""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from scripts import assign_batches


class AssignBatchesTests(unittest.TestCase):
    def test_no_batches(self):
        self.assertEqual(assign_batches.assign([], 4), [])

    def test_two_or_fewer_batches_stay_in_one_group(self):
        groups = assign_batches.assign([('b-002', 120), ('b-001', 50)], 4)
        self.assertEqual(groups, [['b-001', 'b-002']])

    def test_every_batch_assigned_once_and_balanced(self):
        batches = [(f'b-{i:03d}', 120) for i in range(1, 33)] + [('b-033', 60)]
        groups = assign_batches.assign(batches, 4)
        self.assertEqual(len(groups), 4)
        flat = [path for group in groups for path in group]
        self.assertEqual(sorted(flat), sorted(path for path, _ in batches))
        sizes = dict(batches)
        totals = [sum(sizes[path] for path in group) for group in groups]
        self.assertLessEqual(max(totals) - min(totals), 120)

    def test_worker_count_capped_by_batch_count(self):
        groups = assign_batches.assign([('a', 1), ('b', 1), ('c', 1)], 4)
        self.assertEqual(len(groups), 3)

    def test_main_reads_entries_from_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            for index, size in enumerate([3, 2, 1, 1], 1):
                path = Path(directory) / f'batch-{index:03d}.json'
                path.write_text(json.dumps({'en_source': 'x', 'entries': [{}] * size}))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                assign_batches.main(['--pending', directory, '--max-workers', '2'])
            groups = json.loads(out.getvalue())['workers']
            self.assertEqual(len(groups), 2)
            self.assertEqual(sum(len(group) for group in groups), 4)


if __name__ == '__main__':
    unittest.main()
