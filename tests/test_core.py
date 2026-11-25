import copy
import itertools
import random
import unittest

from grace_split import InputError, analyze


def replay(document, lag):
    """Independent operational oracle: mutable retained windows and row-by-row firing."""
    grace = document['budget']-lag
    width, times = document['window'], document['events']
    states, history = {}, {}
    accepted, dropped = [], []
    watermark = high = None
    peak = 0
    for row, time in enumerate(times, 1):
        # Repeated addition on small test timestamps, independent of floor division.
        end = width
        while end <= time:
            end += width
        if watermark is not None and watermark >= end+grace:
            dropped.append(row)
        else:
            accepted.append(row)
            if end not in states:
                states[end] = {'start': end-width, 'end': end, 'accepted_records': [],
                               'revision_records': [], 'first_emission_row': None}
                history[end] = states[end]
            state = states[end]
            state['accepted_records'].append(row)
            if state['first_emission_row'] is not None:
                state['revision_records'].append(row)
        peak = max(peak, len(states))
        high = time if high is None else max(high, time)
        watermark = high-lag
        for end in sorted(list(states)):
            state = states[end]
            if state['first_emission_row'] is None and watermark >= end:
                state['first_emission_row'] = row
                state['first_emission_kind'] = 'watermark'
                state['initial_count'] = len(state['accepted_records'])
            if watermark >= end+grace:
                state['cleanup_row'] = row
                state['cleanup_kind'] = 'watermark'
                del states[end]
    for state in states.values():
        if state['first_emission_row'] is None:
            state['first_emission_row'] = len(times)+1
            state['first_emission_kind'] = 'eof'
            state['initial_count'] = len(state['accepted_records'])
        state['cleanup_row'] = len(times)+1
        state['cleanup_kind'] = 'eof'
    windows = [history[end] for end in sorted(history)]
    for state in windows:
        state['final_count'] = len(state['accepted_records'])
    metrics = {'revisions': sum(len(w['revision_records']) for w in windows),
               'first_emission_row_sum': sum(w['first_emission_row'] for w in windows),
               'initial_member_total': sum(w['initial_count'] for w in windows),
               'eof_windows': sum(w['first_emission_kind']=='eof' for w in windows)}
    return dict(accepted=accepted, dropped=dropped, peak=peak, windows=windows, metrics=metrics)


def doc(events, width=10, budget=6):
    return dict(window=width, budget=budget, events=events)


class CoreTests(unittest.TestCase):
    def compare(self, document, lag):
        saved = copy.deepcopy(document)
        result = analyze(document, lag)
        expected = replay(document, lag)
        self.assertEqual(document, saved)
        self.assertEqual(result['accepted_records'], expected['accepted'])
        self.assertEqual(result['dropped_records'], expected['dropped'])
        self.assertEqual(result['peak_retained_windows'], expected['peak'])
        self.assertEqual(result['selected']['windows'], expected['windows'])
        self.assertEqual(result['selected']['metrics'], expected['metrics'])
        self.assertEqual(result['selected']['grace'], document['budget']-lag)
        self.assertEqual(result['eof_row'], len(document['events'])+1)
        return result

    def test_exhaustive_traces_all_small_budget_splits(self):
        models = splits = 0
        for length in range(5):
            for times in itertools.product([0, 3, 6], repeat=length):
                for width, budget in itertools.product([2, 4], range(5)):
                    document = doc(list(times), width, budget)
                    result = self.compare(document, budget//2)
                    regions = result['regions']
                    self.assertEqual(regions[0]['lag_min'], 0)
                    self.assertEqual(regions[-1]['lag_max'], budget)
                    for a, b in zip(regions, regions[1:]):
                        self.assertEqual(a['lag_max']+1, b['lag_min'])
                        self.assertNotEqual(a['metrics'], b['metrics'])
                    first_zero = None
                    for lag in range(budget+1):
                        expected = replay(document, lag)
                        region = next(r for r in regions if r['lag_min'] <= lag <= r['lag_max'])
                        self.assertEqual(region['metrics'], expected['metrics'])
                        self.assertEqual(result['accepted_records'], expected['accepted'])
                        self.assertEqual(result['dropped_records'], expected['dropped'])
                        self.assertEqual(result['peak_retained_windows'], expected['peak'])
                        if expected['metrics']['revisions'] == 0 and first_zero is None:
                            first_zero = lag
                        splits += 1
                    self.assertEqual(result['least_lag_without_revisions'], first_zero)
                    models += 1
        self.assertEqual((models, splits), (1210, 3630))

    def test_seeded_traces_and_region_endpoints(self):
        rng = random.Random(251126)
        for _ in range(200):
            document = doc([rng.randrange(101) for _ in range(rng.randrange(15))], rng.randrange(1, 21), rng.randrange(21))
            result = self.compare(document, rng.randrange(document['budget']+1))
            for region in result['regions']:
                for lag in {region['lag_min'], region['lag_max']}:
                    self.assertEqual(region['metrics'], replay(document, lag)['metrics'])

    def test_tradeoff_and_first_result_rows(self):
        document = doc([1, 14, 4, 18, 6, 25, 3])
        zero = self.compare(document, 0)
        five = self.compare(document, 5)
        six = self.compare(document, 6)
        self.assertEqual(zero['dropped_records'], [5, 7])
        self.assertEqual(zero['accepted_records'], [1, 2, 3, 4, 6])
        self.assertEqual(zero['selected']['metrics']['revisions'], 1)
        self.assertEqual(five['selected']['metrics']['revisions'], 0)
        self.assertEqual([r['lag_min'] for r in zero['regions']], [0, 5, 6])
        self.assertEqual(zero['selected']['windows'][0]['first_emission_row'], 2)
        self.assertEqual(five['selected']['windows'][0]['first_emission_row'], 4)
        self.assertEqual(six['selected']['metrics']['eof_windows'], 2)
        self.assertEqual(zero['required_budget_for_all'], 16)

    def test_cleanup_equality_and_half_open_membership(self):
        r = self.compare(doc([0, 10, 9, 20, 19], budget=0), 0)
        self.assertEqual(r['dropped_records'], [3, 5])
        self.assertEqual(r['selected']['windows'][0]['cleanup_row'], 2)
        self.assertEqual(r['events'][1]['window_end'], 20)
        # At H=end+B, a following event is rejected, not accepted on equality.
        self.assertEqual(self.compare(doc([0, 16, 9]), 3)['dropped_records'], [3])

    def test_first_arrival_after_firing_threshold_is_not_revision(self):
        r = self.compare(doc([14, 4, 5, 18]), 0)
        window = r['selected']['windows'][0]
        self.assertEqual(window['first_emission_row'], 2)
        self.assertEqual(window['initial_count'], 1)
        self.assertEqual(window['revision_records'], [3])

    def test_zero_grace_has_no_revisions(self):
        self.assertEqual(self.compare(doc([0, 19, 3, 12, 5]), 6)['selected']['metrics']['revisions'], 0)

    def test_empty_and_repeated_timestamps(self):
        empty = self.compare(doc([], budget=10**9), 10**9)
        self.assertEqual(len(empty['regions']), 1)
        self.assertEqual(empty['regions'][0]['lag_max'], 10**9)
        self.assertEqual(empty['peak_retained_windows'], 0)
        repeated = self.compare(doc([3, 3, 3], budget=0), 0)
        self.assertEqual(repeated['selected']['windows'][0]['initial_count'], 3)

    def test_observed_minimum_budget_by_replay(self):
        times = [0, 15, 4, 29, 8]
        required = analyze(doc(times))['required_budget_for_all']
        self.assertTrue(replay(doc(times, budget=required-1), 0)['dropped'])
        self.assertEqual(replay(doc(times, budget=required), 0)['dropped'], [])

    def test_large_budget_is_not_enumerated(self):
        r = analyze(doc([1, 10**12, 2], width=10**9, budget=10**9), 10**9)
        self.assertLessEqual(len(r['regions']), 10)
        self.assertEqual(r['dropped_records'], [3])
        self.assertGreater(r['required_budget_for_all'], 10**9)

    def test_event_bound_and_monotone_summaries(self):
        r = analyze(doc([i*i*12345 for i in range(64)], width=997, budget=10**9))
        self.assertLessEqual(len(r['regions']), 64*64+1)
        self.assertEqual(len(r['accepted_records']), 64)
        for a,b in zip(r['regions'], r['regions'][1:]):
            self.assertLessEqual(a['metrics']['first_emission_row_sum'], b['metrics']['first_emission_row_sum'])
            self.assertGreaterEqual(a['metrics']['revisions'], b['metrics']['revisions'])

    def test_invalid_schema_types_and_bounds(self):
        bad = [None, [], {}, dict(doc([]), extra=1)]
        for key, values in [('window', [0, -1, True, 1.0, 10**9+1]), ('budget', [-1, True, 2.0, 10**9+1]),
                            ('events', [None, {}, [True], [1.0], [-1], [10**12+1], [0]*65])]:
            for value in values:
                item = doc([]); item[key] = value; bad.append(item)
        for item in bad:
            with self.subTest(item=item), self.assertRaises(InputError): analyze(item)
        for lag in [-1, True, 1.0, 7, '2']:
            with self.assertRaises(InputError): analyze(doc([]), lag)


if __name__ == '__main__':
    unittest.main()
