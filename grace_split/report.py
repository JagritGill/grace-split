"""Deterministic summaries in arrival-row units, never wall-clock latency."""


def render(report):
    selected = report['selected']
    lines = [f"grace-split: window={report['window']} budget={report['budget']} events={report['event_count']}",
             f"accepted={report['accepted_records']} dropped={report['dropped_records']}",
             f"peak retained windows={report['peak_retained_windows']}; required budget for all={report['required_budget_for_all']}",
             f"selected lag={selected['lag']} grace={selected['grace']}; revisions={selected['metrics']['revisions']}"]
    for region in report['regions']:
        m = region['metrics']
        lines.append(f"lag [{region['lag_min']},{region['lag_max']}]: revisions={m['revisions']} first_row_sum={m['first_emission_row_sum']} initial_members={m['initial_member_total']} eof_windows={m['eof_windows']}")
    lines.append(f"least lag without revisions={report['least_lag_without_revisions']}")
    lines.append('Finite declared model; row positions are not wall-clock latency or engine guarantees.')
    return '\n'.join(lines)
