#!/usr/bin/env python3
"""Regime timeline: records every change of each coin's regime. Pure stdlib, writes regime.json. Real data only.

Regime = same four states the page shows (radarCard), from the daily CLOSE vs its 21-day and 150-day average (average includes the day):
  up        = above 150 and above 21        pullback = above 150, below 21
  attempt   = below 150, above 21           down     = below 150 and below 21
A 'major' change is one where the close crosses the 150-day average (above<->below); the others are only the 21-day line.
Series are built exactly like the page: BTC = CoinMetrics price.json before Coinalyze starts + Coinalyze daily closes; other coins
= Coinalyze closes; only CLOSED days (day < day of fetch); single-day gaps (<6 days) carried forward.

Each event: coin, day, date, from, to, close, dist150, major, live, seen_at.
  live=false : computed afterwards from past daily closes (history / back-fill).
  live=true  : this job saw the change the first time it ran after the close; seen_at = UTC time it was recorded.
Annotations (live, seen_at) are kept from the previous regime.json; events are otherwise re-derived from data each run.
"""
import json, os, time, datetime
DAY = 86400
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COINS = ['BTC', 'ETH', 'BNB', 'SUI']
RV = 1
START_DAY = 17167  # 2017-01-01: events are kept from here (older ones are not needed and would only make the file heavy)

def load(f):
    return json.load(open(os.path.join(ROOT, f)))

def iso(d):
    return datetime.datetime.fromtimestamp(d * DAY, datetime.timezone.utc).strftime('%Y-%m-%d')

def series(sym, oh, price, today_day):
    s = next((x for x in oh['data'] if str(x['symbol']).startswith(sym)), None)
    if not s: return None
    rows = []
    if sym == 'BTC' and price:
        first = s['history'][0]['t'] // DAY
        rows += [(r[0] // DAY, r[1]) for r in price['rows'] if r[0] // DAY < first]
    rows += [(x['t'] // DAY, x['c']) for x in s['history'] if x['t'] // DAY < today_day]
    rows.sort()
    out = []
    for d, c in rows:
        while out and 1 < d - out[-1][0] < 6: out.append((out[-1][0] + 1, out[-1][1]))
        out.append((d, c))
    return [x[0] for x in out], [x[1] for x in out]

def sma(c, n):
    o = [None] * len(c); s = 0.0
    for i, v in enumerate(c):
        s += v
        if i >= n: s -= c[i - n]
        if i >= n - 1: o[i] = s / n
    return o

def regime_of(a150, a21):
    return 'up' if a150 and a21 else 'pullback' if a150 else 'attempt' if a21 else 'down'

def main():
    oh = load('ohlcv.json'); price = load('price.json')
    today_day = oh['fetched'] // DAY
    now = int(time.time())
    try:
        old = load('regime.json')
    except Exception:
        old = {}
    old_ev = {(e['coin'], e['day']): e for e in old.get('events', [])}
    old_last = (old.get('last_day') or {})
    events, cur, last_day = [], {}, {}
    for sym in COINS:
        sr = series(sym, oh, price, today_day)
        if not sr or len(sr[1]) < 200: continue
        D, C = sr; n = len(C); s21, s150 = sma(C, 21), sma(C, 150)
        last_day[sym] = D[-1]
        prev = None; since = None
        for i in range(149, n):
            a150, a21 = C[i] >= s150[i], C[i] >= s21[i]
            r = regime_of(a150, a21)
            if prev is not None and r != prev[0] and D[i] >= START_DAY:
                key = (sym, D[i]); o = old_ev.get(key)
                if o is not None: live, seen = o.get('live', False), o.get('seen_at')
                elif sym in old_last and D[i] > old_last[sym]: live, seen = True, now
                else: live, seen = False, None
                events.append({'coin': sym, 'day': D[i], 'from': prev[0], 'to': r, 'close': float('%.6g' % C[i]), 'dist150': round(C[i] / s150[i] - 1, 4),
                               'major': prev[1] != a150, 'live': live, 'seen_at': seen})
            if prev is not None and r != prev[0]: since = D[i]
            if prev is None: since = D[i]
            prev = (r, a150)
        cur[sym] = {'regime': prev[0], 'since_day': since, 'since': iso(since), 'days_in': D[-1] - since + 1, 'last_day': iso(D[-1]), 'close': float('%.6g' % C[-1]), 'dist150': round(C[-1] / s150[-1] - 1, 4)}
    events.sort(key=lambda e: (e['day'], e['coin']))
    out = {'rv': RV, 'last_day': last_day, 'current': cur, 'events': events,
           'note': 'live=false: computed afterwards from past daily closes; live=true: seen by the hourly job (seen_at = UTC time recorded). major = close crossed the 150-day average.'}
    body = json.dumps(out, separators=(',', ':'))
    prev_body = None
    if old:
        o2 = dict(old); o2.pop('updated', None); prev_body = json.dumps(o2, separators=(',', ':'))
    if body != prev_body:   # rewrite only when something changed (no hourly commit churn)
        out['updated'] = now
        json.dump(out, open(os.path.join(ROOT, 'regime.json'), 'w'), separators=(',', ':'))
    print('regime events', len(events), {k: v['regime'] + ' since ' + v['since'] for k, v in cur.items()})

if __name__ == '__main__':
    main()
