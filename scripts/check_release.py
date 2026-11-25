"""Exact release inventory, local links, syntax and heuristic disclosure patterns."""
import ast
from pathlib import Path
import re
import stat
from urllib.parse import unquote, urlsplit

FILES = frozenset('''
.github/workflows/verify.yml
.gitignore
AGENTS.md
LICENSE
NOTICE.md
README.md
docs/architecture.md
docs/related-work.md
examples/boundary.json
examples/empty.json
examples/first-late.json
examples/tradeoff.json
grace_split/__init__.py
grace_split/__main__.py
grace_split/core.py
grace_split/input.py
grace_split/report.py
scripts/check_examples.py
scripts/check_release.py
tests/test_cli.py
tests/test_core.py
tests/test_release.py
'''.split())
PATTERNS = (r'AKIA[0-9A-Z]{16}', r'gh[pousr]_[A-Za-z0-9]{30,}',
            r'-----BEGIN [A-Z ]*PRIVATE KEY-----', r'/(?:Users|home)/[A-Za-z0-9_.-]+/')


def check(root):
    root = Path(root).resolve()
    found = set()
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if relative.parts[0] == '.git':
            continue
        if path.is_symlink():
            raise ValueError('release symlink')
        if not path.is_dir():
            found.add(relative.as_posix())
    if found != FILES:
        raise ValueError(f'inventory: missing={sorted(FILES-found)} extra={sorted(found-FILES)}')
    links = syntax = 0
    for name in sorted(FILES):
        path = root/name
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o644 or info.st_size > 100000:
            raise ValueError(f'file mode/size: {name}')
        source = path.read_text(encoding='utf-8')
        if any(ord(c) < 32 and c not in '\n\t' for c in source):
            raise ValueError(f'control byte: {name}')
        if any(re.search(pattern, source) for pattern in PATTERNS):
            raise ValueError(f'disclosure pattern: {name}')
        if name.endswith('.py'):
            ast.parse(source, filename=name)
            syntax += 1
        if name.endswith('.md'):
            for raw in re.findall(r'\]\(([^)]+)\)', source):
                target = urlsplit(raw)
                if target.scheme or not target.path:
                    continue
                resolved = (path.parent/unquote(target.path)).resolve()
                if not resolved.is_relative_to(root) or not resolved.is_file():
                    raise ValueError(f'local link: {name}')
                links += 1
    return dict(files=len(FILES), local_links=links, python_syntax_files=syntax)


if __name__ == '__main__':
    print(check(Path(__file__).resolve().parents[1]))
