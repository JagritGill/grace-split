import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    return subprocess.run([sys.executable, '-B', '-m', 'grace_split', *map(str,args)],
                          cwd=ROOT, capture_output=True, text=True, timeout=15)


class CliTests(unittest.TestCase):
    def test_selected_and_common_gates(self):
        for args, code in [((),0), (('--max-dropped','1'),1), (('--max-dropped','2'),0),
                           (('--max-revisions','0'),1), (('--lag','5','--max-revisions','0'),0),
                           (('--lag','5','--max-dropped','1','--max-revisions','0'),1)]:
            r = run('examples/tradeoff.json','--json',*args)
            self.assertEqual(r.returncode,code); self.assertEqual(r.stderr,'')
            self.assertEqual(json.loads(r.stdout)['dropped_records'],[5,7])
        r = run('examples/empty.json')
        self.assertEqual(r.returncode,0); self.assertIn('accepted=[] dropped=[]',r.stdout)

    def bad(self,data):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder,'trace.json'); path.write_bytes(data); r=run(path)
        self.assertEqual(r.returncode,2); self.assertEqual(r.stdout,''); self.assertNotIn('Traceback',r.stderr)

    def test_parser_rejections(self):
        for data in [b'{',b'null',b'NaN',b'Infinity',b'1'*5000,b'['*2000+b']'*2000,
                     b'{"window":1,"window":2}',b'\xff',b'\xef\xbb\xbf{}']:
            self.bad(data)

    def test_exact_file_byte_limit(self):
        data=(ROOT/'examples/empty.json').read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder,'trace.json'); path.write_bytes(data+b' '*(32768-len(data)))
            self.assertEqual(run(path).returncode,0)
        self.bad(data+b' '*(32769-len(data)))

    def test_nonregular_missing_symlink(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'data').write_text('{}'); (root/'link').symlink_to(root/'data'); os.mkfifo(root/'fifo')
            for path in [root,root/'link',root/'fifo',root/'missing']:
                r=run(path); self.assertEqual(r.returncode,2); self.assertEqual(r.stdout,'')

    def test_invalid_arguments_and_model(self):
        for args in [('--lag','-1'),('--lag','7'),('--lag','x'),('--max-dropped','-1'),('--max-revisions','65'),('--unknown',)]:
            r=run('examples/tradeoff.json',*args)
            self.assertEqual(r.returncode,2); self.assertEqual(r.stdout,'')
        self.bad(b'{"window":0,"budget":0,"events":[]}')


if __name__ == '__main__':
    unittest.main()
