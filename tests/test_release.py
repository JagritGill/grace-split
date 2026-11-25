from pathlib import Path
import shutil
import tempfile
import unittest
from scripts.check_release import FILES, check

ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.root=Path(folder.name)
        for name in FILES:
            target=self.root/name; target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,target)

    def test_exact_inventory(self):
        self.assertEqual(check(self.root)['files'],22)
        extra=self.root/'extra'; extra.write_text('synthetic')
        with self.assertRaises(ValueError):check(self.root)
        extra.unlink(); (self.root/'LICENSE').unlink()
        with self.assertRaises(ValueError):check(self.root)

    def test_disclosure_negative_controls(self):
        for value in ['AK'+'IA'+'Z'*16,'gh'+'p_'+'a'*36,'/'+'Users'+'/synthetic/file','-----BEGIN '+'RSA PRIVATE KEY-----']:
            (self.root/'NOTICE.md').write_text(value)
            with self.assertRaises(ValueError):check(self.root)

    def test_links_modes_symlinks(self):
        p=self.root/'NOTICE.md'; p.write_text('[missing](missing.md)')
        with self.assertRaises(ValueError):check(self.root)
        p.write_text('safe'); p.chmod(0o755)
        with self.assertRaises(ValueError):check(self.root)
        p.unlink(); p.symlink_to(self.root/'README.md')
        with self.assertRaises(ValueError):check(self.root)

    def test_syntax_and_control_bytes(self):
        p=self.root/'grace_split/__init__.py'; p.write_text('def (')
        with self.assertRaises(SyntaxError):check(self.root)
        p.write_text('"valid"\n'); (self.root/'NOTICE.md').write_bytes(b'x\x00')
        with self.assertRaises(ValueError):check(self.root)


if __name__ == '__main__':
    unittest.main()
