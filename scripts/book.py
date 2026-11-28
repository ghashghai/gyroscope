#!/usr/bin/env python3
"""Paper account of the whole program ("حسابداری"): writes book.json. Pure stdlib, real daily closes only, nothing back-filled.

Hypothetical capital 1000 at the start day (the user's choice). Split fixed in advance:
  core = 1/3 (USDT, never touched) ; the other 2/3 is split equally between BTC, ETH, BNB, SUI ; each coin bucket = 7 equal parts.
Per coin the 7 parts are assigned like this:
  4+2 parts TREND  : buy one part every 2 days while the close is above both its 150-day and 21-day average (max 4 parts; max 6 when the close is >= 10% above the 150-day
                     average = 'strong' parts); sell all when the close is below the 150-day average. (Aggressive version, chosen 2026-11-28 after history tests.)
  1 part   CHANNEL : experiment (paper), BTC and SUI only (for ETH and BNB this part is idle cash). Active only while close >= 150-day average. Channel [L, L*1.07]: buy near L, sell at U, stop 7% below L; if the price escapes the
                     channel the part moves to the next channel. 
  RESERVE          : none for BTC/SUI; for ETH/BNB the channel part stays idle cash (1 part).
Signals use the close of day i, fills use the close of day i+1 (a real closed price). Fee 0.2% per fill. Part size is fixed at bucket/7 (profits and losses stay in their pool).
ENGAGED = value of coins held at the last closed price. FREE = all cash (core + idle parts + unused slots). ENGAGED + FREE = TOTAL (checked).
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regime import series, sma, load, iso, DAY, ROOT
FEE, W, RV = 0.002, 0.07, 2
GAP, STRONG = 2, 0.10   # aggressive trend: one part every 2 days; 2 extra 'strong' parts when the close is >= 10% above the 150-day average
COINS = ['BTC', 'ETH', 'BNB', 'SUI']
CHANNEL_COINS = ('BTC', 'SUI')   # ETH and BNB channel removed 2026-11-27 (tested median 0.83/0.84 per year): their channel part stays idle cash
CAPITAL = 1000.0
CORE = CAPITAL / 3
BUCKET = CAPITAL * 2 / 3 / 4
PART = BUCKET / 7

def new_coin():
    return {'trend': {'cash': 6 * PART, 'units': 0.0, 'parts': 0, 'last_buy_day': -99, 'pending': None},
            'chan': {'cash': PART, 'units': 0.0, 'L': None, 'U': None, 'active': False, 'pending': None}, 'reserve': 0.0, 'last_day': None}

def fill(pool, c, trades, coin, eng, day):
    p = pool['pending']
    if not p: return
    if p['side'] == 'buy':
        spend = min(p.get('amount', pool['cash']), pool['cash'] / (1 + FEE))
        if spend > 1e-9:
            pool['units'] += spend / c; pool['cash'] -= spend * (1 + FEE); pool['cost'] = pool.get('cost', 0.0) + spend * (1 + FEE)
            if eng == 'trend': pool['parts'] += 1
            trades.append({'coin': coin, 'engine': eng, 'day': day, 'date': iso(day), 'side': 'buy', 'price': float('%.6g' % c), 'amount': round(spend, 2), 'why': p['why']})
    else:
        if pool['units'] > 0:
            got = pool['units'] * c * (1 - FEE)
            pnl = got - pool.get('cost', 0.0)
            trades.append({'coin': coin, 'engine': eng, 'day': day, 'date': iso(day), 'side': 'sell', 'price': float('%.6g' % c), 'amount': round(got, 2), 'why': p['why'], 'pnl': round(pnl, 2)})
            pool['cash'] += got; pool['units'] = 0.0; pool['cost'] = 0.0
            if eng == 'trend': pool['parts'] = 0
    pool['pending'] = None

def step(st, coin, i, D, C, S21, S150, trades):
    c, day = C[i], D[i]; a150 = c >= S150[i]; a21 = c >= S21[i]
    T, H = st['trend'], st['chan']
    fill(T, c, trades, coin, 'trend', day); fill(H, c, trades, coin, 'channel', day)
    # trend engine
    if not a150:
        if T['units'] > 0: T['pending'] = {'side': 'sell', 'why': 'below 150-day average'}
    elif a21 and T['parts'] < (6 if c / S150[i] - 1 >= STRONG else 4) and (T['parts'] == 0 or day - T['last_buy_day'] >= GAP):
        T['pending'] = {'side': 'buy', 'amount': PART, 'why': 'uptrend part %d' % (T['parts'] + 1)}; T['last_buy_day'] = day
    # channel engine
    if coin not in CHANNEL_COINS:
        st['last_day'] = day; return
    if not a150:
        H['active'] = False; H['L'] = None
        if H['units'] > 0: H['pending'] = {'side': 'sell', 'why': 'trend off'}
    else:
        H['active'] = True
        if H['L'] is None: H['L'] = c / (1 + W / 2); H['U'] = H['L'] * (1 + W)
        if H['units'] == 0:
            while c > H['U']: H['L'] = H['U']; H['U'] = H['L'] * (1 + W)
            while c < H['L'] * (1 - W): H['U'] = H['L']; H['L'] = H['U'] / (1 + W)
            if c <= H['L'] * 1.01 and c >= H['L'] * (1 - W): H['pending'] = {'side': 'buy', 'why': 'channel low'}
        else:
            if c >= H['U']: H['pending'] = {'side': 'sell', 'why': 'channel top'}; H['L'] = H['U']; H['U'] = H['L'] * (1 + W)
            elif c <= H['L'] * (1 - W): H['pending'] = {'side': 'sell', 'why': 'channel stop'}; H['U'] = H['L']; H['L'] = H['U'] / (1 + W)
    st['last_day'] = day

def main():
    oh = load('ohlcv.json'); price = load('price.json'); today_day = oh['fetched'] // DAY
    try: old = load('book.json')
    except Exception: old = None
    data = {}
    for sym in COINS:
        sr = series(sym, oh, price, today_day)
        if not sr or len(sr[1]) < 200: continue
        D, C = sr; data[sym] = (D, C, sma(C, 21), sma(C, 150))
    if old and old.get('rv') == RV:
        coins, trades, start = old['_state'], old['trades'], old['start_day']
    else:
        coins, trades = {s: new_coin() for s in data}, []
        start = min(v[0][-1] for v in data.values())
    for sym, (D, C, S21, S150) in data.items():
        st = coins[sym]; idx = {d: i for i, d in enumerate(D)}
        if st['last_day'] is None:   # start day: signals only, nothing is replayed
            i = idx.get(start, len(D) - 1); step(st, sym, i, D, C, S21, S150, []); first = i + 1
        else:
            first = idx.get(st['last_day'], len(D) - 1) + 1
        for i in range(first, len(D)): step(st, sym, i, D, C, S21, S150, trades)
    rows = []; tot_e = tot_f = 0.0
    for sym, (D, C, S21, S150) in data.items():
        st = coins[sym]; c = C[-1]; T, H = st['trend'], st['chan']
        te, he = T['units'] * c, H['units'] * c
        free = T['cash'] + H['cash'] + st['reserve']; eng = te + he
        rows.append({'coin': sym, 'close': float('%.6g' % c), 'engaged': round(eng, 2), 'free': round(free, 2), 'total': round(eng + free, 2),
                     'trend_parts': T['parts'], 'trend_value': round(te, 2), 'trend_pending': (T['pending'] or {}).get('side'),
                     'chan_state': 'none' if sym not in CHANNEL_COINS else ('in' if H['units'] > 0 else ('on' if H['active'] else 'off')), 'chan_value': round(he + H['cash'], 2),
                     'chan_L': float('%.6g' % H['L']) if H['L'] else None, 'chan_U': float('%.6g' % H['U']) if H['U'] else None, 'chan_pending': (H['pending'] or {}).get('side'),
                     'reserve': round(st['reserve'], 2), 'units': float('%.8g' % (T['units'] + H['units'])), 'cost': round(T.get('cost', 0.0) + H.get('cost', 0.0), 2),
                     'realized': round(sum(t.get('pnl', 0.0) for t in trades if t['coin'] == sym), 2), 'last_day': iso(D[-1]), 'sma150': float('%.6g' % S150[-1])})
        tot_e += eng; tot_f += free
    total = tot_e + tot_f + CORE
    assert abs(total - sum(r['total'] for r in rows) - CORE) < 0.03, 'accounting does not add up'
    out = {'rv': RV, 'start_day': start, 'start': iso(start), 'capital': CAPITAL, 'core': round(CORE, 2),
           'total': round(total, 2), 'engaged': round(tot_e, 2), 'free': round(tot_f + CORE, 2), 'pnl_pct': round(total / CAPITAL - 1, 5),
           'coins': rows, 'trades': trades[-60:], 'n_trades': len(trades), 'trades_by_engine': {e: sum(1 for t in trades if t['engine'] == e) for e in ('trend', 'channel')},
           'note': 'Paper account of a hypothetical 1000, started on the day shown; nothing before start is replayed. Marked at the last closed daily price. Tested rules, not a forecast.',
           '_state': coins, 'trades_all_count': len(trades)}
    out['trades'] = trades   # full log (small)
    prev = None
    if old:
        o2 = dict(old); o2.pop('updated', None); prev = json.dumps(o2, separators=(',', ':'))
    body = json.dumps(out, separators=(',', ':'))
    if body != prev:
        out['updated'] = int(time.time()); json.dump(out, open(os.path.join(ROOT, 'book.json'), 'w'), separators=(',', ':'))
    print('book total %.2f engaged %.2f free %.2f trades %d' % (total, tot_e, tot_f + CORE, len(trades)))

if __name__ == '__main__':
    main()
