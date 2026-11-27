#!/usr/bin/env python3
"""Macro test: does any macro reading (stablecoin total, dollar, US 10y, TGA, reverse repo) carry information about BTC
beyond the trend rule? Real data only, pure stdlib (runs locally or in Actions). Writes macro_test.json.

Method (all in-sample unless marked OOS; daily observations overlap heavily, so independent samples ~ days/90):
  * BTC daily close = CoinMetrics price.json up to its last day, then Coinalyze BTC perp daily close (checked: median diff 0.04%).
    The last Coinalyze day is dropped if it was still open when fetched.
  * Features use only data available on that day (as-of lookup, no look-ahead):
      stable_chg30  = % change of total stablecoin supply over 30 days (only when supply >= 5bn on both days)
      dollar_chg30  = % change of broad dollar index, us10y_d30 = change of US 10y yield in points,
      tga_chg30     = % change of Treasury cash account, rrp_d30 = change of reverse repo in billions.
  * State = BTC close above / below its 150-day average. Outcomes: fwd30 = BTC return over next 30 days,
    hit20 = BTC falls at least 20% below today's close at some point within the next 90 days.
  * For each feature and state: terciles (low/mid/high), difference high-minus-low for fwd30 and hit20 in the whole sample,
    in the first half, in the second half (same cutoffs), and OOS (cutoffs from the first half only, applied to the second half).
  * PASS = same sign in first half, second half and OOS for BOTH outcomes (higher fwd30 <-> lower hit20 is the consistent
    pairing), and |hit20 difference| >= 10 points in both halves. 5 features x 2 states = 10 looks: one or two passes can be luck.
"""
import json, bisect, datetime, os
DAY = 86400
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

def load(f):
    return json.load(open(os.path.join(ROOT, f)))

def iso(d):
    return datetime.datetime.fromtimestamp(d * DAY, datetime.timezone.utc).strftime('%Y-%m-%d')

def day_of(s):
    return int(datetime.datetime.strptime(s, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc).timestamp()) // DAY

def btc_series():
    cm = {r[0] // DAY: r[1] for r in load('price.json')['rows']}
    oh = load('ohlcv.json')
    h = [x for x in oh['data'] if x['symbol'].startswith('BTC')][0]['history']
    last_closed = oh['fetched'] // DAY - 1
    cz = {x['t'] // DAY: x['c'] for x in h if x['t'] // DAY <= last_closed}
    last_cm = max(cm)
    d0 = min(cm); d1 = max(cz)
    C = {}
    for d in range(d0, d1 + 1):
        if d <= last_cm and d in cm: C[d] = cm[d]
        elif d in cz: C[d] = cz[d]
    days = sorted(C)
    assert all(b - a == 1 for a, b in zip(days, days[1:])), 'gap in BTC series'
    return days[0], [C[d] for d in days], last_cm

def asof(series):
    ds = [x[0] for x in series]; vs = [x[1] for x in series]
    def f(d):
        i = bisect.bisect_right(ds, d) - 1
        return vs[i] if i >= 0 else None
    return f, (ds[0] if ds else None), (ds[-1] if ds else None)

def quant(a, q):
    s = sorted(a); k = (len(s) - 1) * q; lo = int(k); hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (k - lo)

def grp(v, c1, c2):
    return 0 if v <= c1 else (2 if v > c2 else 1)

def summarize(rows):
    if not rows: return {'n': 0}
    return {'n': len(rows), 'fwd30_mean': sum(r[2] for r in rows) / len(rows), 'hit20': sum(r[3] for r in rows) / len(rows)}

def sgn(x):
    return 0 if x == 0 else (1 if x > 0 else -1)

def main():
    d0, C, last_cm = btc_series()
    N = len(C); last_day = d0 + N - 1
    macro = load('macro.json')['series']
    sc = [(day_of(r[0]), r[1]) for r in macro['stablecoins_bn']]
    feats = {}
    f_sc, _, _ = asof(sc)
    feats['stable_chg30'] = (lambda d: (f_sc(d) / f_sc(d - 30) - 1) if f_sc(d) and f_sc(d - 30) and f_sc(d) >= 5 and f_sc(d - 30) >= 5 else None, 'stablecoin total, 30d % change')
    def mk(name, kind, label):
        s = [(day_of(r[0]), r[1]) for r in macro[name]]
        f, a, b = asof(s)
        def g(d):
            if a is None or d - 30 < a: return None
            x, y = f(d), f(d - 30)
            if x is None or y is None: return None
            if kind == 'pct': return (x / y - 1) if y else None
            return x - y
        return g, label
    feats['dollar_chg30'] = mk('dollar_broad', 'pct', 'broad dollar index, 30d % change')
    feats['us10y_d30'] = mk('us10y', 'abs', 'US 10y yield, 30d change (points)')
    feats['tga_chg30'] = mk('tga_bn', 'pct', 'Treasury cash account, 30d % change')
    feats['rrp_d30'] = mk('reverse_repo_bn', 'abs', 'reverse repo, 30d change (billions)')

    sma = [None] * N; acc = 0.0
    for i in range(N):
        acc += C[i]
        if i >= 150: acc -= C[i - 150]
        if i >= 149: sma[i] = acc / 150
    out = {'btc_first_day': iso(d0), 'btc_last_day': iso(last_day), 'coinmetrics_last_day': iso(last_cm), 'features': {}}
    for name, (fn, label) in feats.items():
        base = []
        for i in range(150, N - 90):
            d = d0 + i; v = fn(d)
            if v is None: continue
            fwd = C[i + 30] / C[i] - 1; mn = min(C[i + 1:i + 91]) / C[i] - 1
            base.append((d, v, fwd, 1 if mn <= -0.20 else 0, 'above' if C[i] > sma[i] else 'below'))
        res = {'label': label, 'first_day': iso(base[0][0]) if base else None, 'last_day': iso(base[-1][0]) if base else None, 'states': {}}
        for st in ('above', 'below'):
            rows = [(d, v, f, h) for d, v, f, h, s in base if s == st]
            if len(rows) < 150:
                res['states'][st] = {'n': len(rows), 'note': 'too short to test'}; continue
            vals = [r[1] for r in rows]; c1, c2 = quant(vals, 1 / 3), quant(vals, 2 / 3)
            mid_day = sorted(r[0] for r in rows)[len(rows) // 2]
            H1 = [r for r in rows if r[0] <= mid_day]; H2 = [r for r in rows if r[0] > mid_day]
            def tern(rs, a, b):
                g = [[], [], []]
                for r in rs: g[grp(r[1], a, b)].append(r)
                return [summarize(x) for x in g]
            whole = tern(rows, c1, c2); t1 = tern(H1, c1, c2); t2 = tern(H2, c1, c2)
            a1, b1 = quant([r[1] for r in H1], 1 / 3), quant([r[1] for r in H1], 2 / 3)
            oos = tern(H2, a1, b1)
            def diff(t):
                if t[0].get('n', 0) < 20 or t[2].get('n', 0) < 20: return None
                return {'hit20': t[2]['hit20'] - t[0]['hit20'], 'fwd30': t[2]['fwd30_mean'] - t[0]['fwd30_mean']}
            dw, d1, d2, do = diff(whole), diff(t1), diff(t2), diff(oos)
            ok = all(x is not None for x in (d1, d2, do))
            passed = False
            if ok:
                same = len({sgn(d1['hit20']), sgn(d2['hit20']), sgn(do['hit20'])}) == 1 and len({sgn(d1['fwd30']), sgn(d2['fwd30']), sgn(do['fwd30'])}) == 1
                paired = sgn(d1['hit20']) == -sgn(d1['fwd30'])
                big = abs(d1['hit20']) >= 0.10 and abs(d2['hit20']) >= 0.10
                passed = bool(same and paired and big)
            res['states'][st] = {'n_days': len(rows), 'independent_approx': round(len(rows) / 90, 1), 'cutoffs': [c1, c2], 'low_mid_high_whole': whole,
                                 'diff_high_minus_low': {'whole': dw, 'first_half': d1, 'second_half': d2, 'oos': do}, 'split_day': iso(mid_day), 'PASS': passed}
        out['features'][name] = res
    json.dump(out, open(os.path.join(ROOT, 'macro_test.json'), 'w'), indent=1)
    # printable report
    print('BTC series %s .. %s (CoinMetrics until %s)' % (out['btc_first_day'], out['btc_last_day'], out['coinmetrics_last_day']))
    for name, r in out['features'].items():
        print('\n== %s  [%s]  usable %s .. %s' % (name, r['label'], r['first_day'], r['last_day']))
        for st, s in r['states'].items():
            if 'note' in s: print('  %-5s n=%d %s' % (st, s['n'], s['note'])); continue
            w = s['low_mid_high_whole']
            print('  %-5s days=%d (~%s independent)  PASS=%s  split %s' % (st, s['n_days'], s['independent_approx'], s['PASS'], s['split_day']))
            for k, nm in enumerate(('low', 'mid', 'high')):
                print('        %-4s n=%-4d fwd30 %+6.1f%%  P(-20%% in 90d) %4.0f%%' % (nm, w[k]['n'], w[k]['fwd30_mean'] * 100, w[k]['hit20'] * 100))
            d = s['diff_high_minus_low']
            fmt = lambda x: 'n/a' if x is None else 'hit20 %+.0fpt fwd30 %+.1fpt' % (x['hit20'] * 100, x['fwd30'] * 100)
            print('        high-low: whole [%s] | H1 [%s] | H2 [%s] | OOS [%s]' % (fmt(d['whole']), fmt(d['first_half']), fmt(d['second_half']), fmt(d['oos'])))

if __name__ == '__main__':
    main()
