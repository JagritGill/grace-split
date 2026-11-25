"""Exact fixed-budget split regions for a finite, explicitly defined window model."""

from bisect import bisect_left, bisect_right

MAX_EVENTS = 64
MAX_PARAMETER = 10**9


class InputError(ValueError):
    """Unsupported model input; messages do not echo input values."""


def _integer(value, low, high):
    return type(value) is int and low <= value <= high


def _validate(document, lag):
    if type(document) is not dict or set(document) != {'window', 'budget', 'events'}:
        raise InputError('expected exactly window, budget and events')
    width, budget, events = document['window'], document['budget'], document['events']
    if not _integer(width, 1, MAX_PARAMETER) or not _integer(budget, 0, MAX_PARAMETER):
        raise InputError('window must be 1..1000000000; budget must be 0..1000000000')
    if type(events) is not list or len(events) > MAX_EVENTS:
        raise InputError('events must be a list of at most 64 timestamps')
    if not all(_integer(t, 0, 10**12) for t in events):
        raise InputError('event timestamps must be integers from 0 through 1000000000000')
    if not _integer(lag, 0, budget):
        raise InputError('lag must be an integer between zero and budget')
    return width, budget, tuple(events)


def _schedule(groups, highs, lag, details=False):
    metrics = dict(revisions=0, first_emission_row_sum=0, initial_member_total=0, eof_windows=0)
    windows = []
    for end, rows in groups.items():
        first = bisect_left(highs, end + lag, lo=rows[0]-1) + 1
        initial = bisect_right(rows, first)
        metrics['revisions'] += len(rows) - initial
        metrics['first_emission_row_sum'] += first
        metrics['initial_member_total'] += initial
        metrics['eof_windows'] += first == len(highs)+1
        if details:
            windows.append({'end': end, 'accepted_records': rows.copy(),
                            'first_emission_row': first,
                            'first_emission_kind': 'eof' if first == len(highs)+1 else 'watermark',
                            'initial_count': initial, 'final_count': len(rows),
                            'revision_records': rows[initial:]})
    return metrics, windows


def analyze(document, lag=0):
    """Compare all integer lag/grace splits and explain one selected split.

    The model is not a compatibility implementation of any streaming framework.
    Input order is arrival order; each row counts once; no live clock or I/O.
    """
    width, budget, times = _validate(document, lag)
    high = None
    highs, ledger, accepted, dropped = [], [], [], []
    groups = {}
    for row, time in enumerate(times, 1):
        end = (time // width + 1) * width
        required = 0 if high is None else max(0, high - end + 1)
        keep = required <= budget
        ledger.append({'record': row, 'event_time': time, 'window_end': end,
                       'high_before': high, 'minimum_budget': required, 'accepted': keep})
        if keep:
            accepted.append(row)
            groups.setdefault(end, []).append(row)
        else:
            dropped.append(row)
        high = time if high is None else max(high, time)
        highs.append(high)
    groups = dict(sorted(groups.items()))
    cleanup = {end: bisect_left(highs, end+budget, lo=rows[0]-1)+1 for end, rows in groups.items()}
    # Peak after admitting a row, before that row's watermark-driven cleanup.
    peak = max((sum(rows[0] <= row <= cleanup[end] for end, rows in groups.items())
                for row in range(1, len(times)+1)), default=0)
    cuts = {0, budget+1}
    for end, rows in groups.items():
        for high in highs[rows[0]-1:]:
            boundary = high-end+1
            if 0 < boundary <= budget:
                cuts.add(boundary)
    cuts = sorted(cuts)
    regions = []
    for left, right in zip(cuts, cuts[1:]):
        metrics, _ = _schedule(groups, highs, left)
        if regions and regions[-1]['metrics'] == metrics:
            regions[-1]['lag_max'] = right-1
            regions[-1]['grace_at_lag_max'] = budget-(right-1)
        else:
            regions.append({'lag_min': left, 'lag_max': right-1,
                            'grace_at_lag_min': budget-left,
                            'grace_at_lag_max': budget-(right-1), 'metrics': metrics})
    metrics, windows = _schedule(groups, highs, lag, True)
    for window in windows:
        window['start'] = window['end']-width
        window['cleanup_row'] = cleanup[window['end']]
        window['cleanup_kind'] = 'eof' if window['cleanup_row'] == len(times)+1 else 'watermark'
    return {'schema_version': 1, 'window': width, 'budget': budget, 'event_count': len(times),
            'eof_row': len(times)+1, 'accepted_records': accepted, 'dropped_records': dropped,
            'required_budget_for_all': max((e['minimum_budget'] for e in ledger), default=0),
            'peak_retained_windows': peak, 'events': ledger, 'regions': regions,
            'least_lag_without_revisions': next(r['lag_min'] for r in regions if r['metrics']['revisions'] == 0),
            'selected': {'lag': lag, 'grace': budget-lag, 'metrics': metrics, 'windows': windows}}
