import argparse
import json
import sys
from . import InputError, analyze
from .input import load
from .report import render


def main(argv=None):
    parser = argparse.ArgumentParser(description='Compare every integer split of a fixed event-time retention budget.')
    parser.add_argument('trace', help='regular local UTF-8 JSON trace')
    parser.add_argument('--lag', type=int, default=0, help='selected watermark lag, 0..budget')
    parser.add_argument('--json', action='store_true', help='emit all exact regions and selected window evidence')
    parser.add_argument('--max-dropped', type=int, help='inclusive dropped-record limit, 0..64')
    parser.add_argument('--max-revisions', type=int, help='inclusive selected-split revision limit, 0..64')
    args = parser.parse_args(argv)
    try:
        if any(v is not None and not 0 <= v <= 64 for v in [args.max_dropped, args.max_revisions]):
            raise InputError('gate limits must be integers from 0 through 64')
        report = analyze(load(args.trace), args.lag)
    except InputError as exc:
        print(f'grace-split: invalid input: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(report, sort_keys=True, indent=2) if args.json else render(report))
    return int((args.max_dropped is not None and len(report['dropped_records']) > args.max_dropped) or
               (args.max_revisions is not None and report['selected']['metrics']['revisions'] > args.max_revisions))


if __name__ == '__main__':
    raise SystemExit(main())
