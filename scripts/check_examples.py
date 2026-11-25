"""Exercise the documented examples and intentional gate outcomes."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    cases = [
        (['examples/tradeoff.json'], 0, 2, 1, 5),
        (['examples/tradeoff.json','--lag','5','--json','--max-revisions','0'], 0, 2, 0, 5),
        (['examples/tradeoff.json','--lag','0','--max-revisions','0'], 1, 2, 1, 5),
        (['examples/tradeoff.json','--lag','5','--max-dropped','1'], 1, 2, 0, 5),
        (['examples/boundary.json','--json'], 0, 2, 0, 0),
        (['examples/first-late.json','--json'], 0, 0, 1, 5),
        (['examples/empty.json'], 0, 0, 0, 0),
        (['examples/tradeoff.json','--lag','6','--json','--max-dropped','2','--max-revisions','0'], 0, 2, 0, 5),
    ]
    for arguments, status, drops, revisions, minimum in cases:
        r = subprocess.run([sys.executable,'-B','-m','grace_split',*arguments],
                           cwd=ROOT, text=True, capture_output=True, timeout=15)
        assert r.returncode == status and not r.stderr, (arguments,r.returncode,r.stderr)
        if '--json' in arguments:
            report=json.loads(r.stdout)
            assert len(report['dropped_records']) == drops
            assert report['selected']['metrics']['revisions'] == revisions
            assert report['least_lag_without_revisions'] == minimum
        else:
            assert f'; revisions={revisions}' in r.stdout
            assert f'least lag without revisions={minimum}' in r.stdout
    print('8 CLI examples passed, including intentional gate exits 1')


if __name__ == '__main__':
    main()
