#!/usr/bin/env python3
"""Channel experiment part (paper trading, BTC only). Pure stdlib, writes channel.json. Real daily closes only; nothing is back-filled.

The part is ONE of the seven parts (value 1.00 at the start, in cash). Rule (fixed in advance, same as the tested rule):
  * Active only while the daily close is at or above the 150-day average (average includes the day). Below it: flat (cash); a held position is sold.
  * Channel [L, U = L*1.07]. First channel when the part becomes active: L = close/1.035.
  * Flat: if the close escaped above U the channel moves up step by step (the part 'declares itself stranded'), if below L*0.93 it moves down;
    then buy when close <= L*1.01 (and >= L*0.93).
  * Holding: close >= U -> sell (channel moves up one step); close <= L*0.93 -> sell (stop; channel moves down one step).
  * Signal on the close of day i, fill at the close of day i+1 (so every fill uses a real, already closed price). Fee 0.2% per fill.
Only closed days are used. The state continues from the previous channel.json; the run is deterministic from data.
"""
import json, os, time, datetime
DAY = 86400
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, FEE, RV = 0.07, 0.002, 1
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regime import series, sma, load, iso

def step(st, c, s150, day, trades):
    """process one closed day: fill pending order at today's close, then new signal."""
    if st['pending']:
        side = st['pending']['side']
        if side == 'buy':
            st['units'] = st['cash'] * (1 - FEE) / c; st['cash'] = 0.0
        else:
            st['cash'] = st['units'] * c * (1 - FEE); st['units'] = 0.0
        trades.append({'day': day, 'date': iso(day), 'side': side, 'price': float('%.6g' % c), 'why': st['pending']['why'], 'signal_day': st['pending']['day'], 'part_value_after': round(st['cash'] + st['units'] * c, 4)})
        st['pending'] = None
    if c < s150:
        st['active'] = False
        if st['units'] > 0: st['pending'] = {'side': 'sell', 'why': 'trend', 'day': day}
        st['L'] = None; return
    st['active'] = True
    if st['L'] is None:
        st['L'] = c / (1 + W / 2); st['U'] = st['L'] * (1 + W)
    if st['units'] == 0:
        while c > st['U']: st['L'] = st['U']; st['U'] = st['L'] * (1 + W)
        while c < st['L'] * (1 - W): st['U'] = st['L']; st['L'] = st['U'] / (1 + W)
        if c <= st['L'] * 1.01 and c >= st['L'] * (1 - W): st['pending'] = {'side': 'buy', 'why': 'channel low', 'day': day}
    else:
        if c >= st['U']:
            st['pending'] = {'side': 'sell', 'why': 'channel top', 'day': day}; st['L'] = st['U']; st['U'] = st['L'] * (1 + W)
        elif c <= st['L'] * (1 - W):
            st['pending'] = {'side': 'sell', 'why': 'stop', 'day': day}; st['U'] = st['L']; st['L'] = st['U'] / (1 + W)

def run(D, C, S150, state, trades, first, last):
    for i in range(first, last + 1):
        step(state, C[i], S150[i], D[i], trades); state['last_day'] = D[i]

def main():
    oh = load('ohlcv.json'); price = load('price.json'); today_day = oh['fetched'] // DAY
    D, C = series('BTC', oh, price, today_day); S150 = sma(C, 150)
    try: old = load('channel.json')
    except Exception: old = None
    if old and old.get('rv') == RV:
        state, trades = old['state'], old['trades']; start = old['start_day']
        idx = {d: i for i, d in enumerate(D)}
        first = idx.get(state['last_day'], len(D) - 1) + 1
    else:  # start today: no history is replayed, the part begins flat in cash
        i = len(D) - 1
        state = {'cash': 1.0, 'units': 0.0, 'pending': None, 'L': None, 'U': None, 'active': False, 'last_day': D[i]}
        trades = []; start = D[i]
        step(state, C[i], S150[i], D[i], []); state['last_day'] = D[i]   # start-day signal (no fill yet)
        first = i + 1
    run(D, C, S150, state, trades, first, len(D) - 1)
    i = len(D) - 1; last = state['last_day']
    value = state['cash'] + state['units'] * C[i]
    out = {'rv': RV, 'start_day': start, 'start': iso(start), 'params': {'width': W, 'stop': W, 'fee': FEE, 'asset': 'BTC', 'gate': 'close >= 150-day average'},
           'state': state, 'trades': trades, 'value': round(value, 4), 'value_day': iso(D[i]), 'close': float('%.6g' % C[i]), 'sma150': float('%.6g' % S150[i]),
           'note': 'Paper trading of one experiment part, started on the day shown. Nothing before start is replayed. 1.00 = value at start. Tested rule, not a forecast.'}
    prev = None
    if old:
        o2 = dict(old); o2.pop('updated', None); prev = json.dumps(o2, separators=(',', ':'))
    body = json.dumps(out, separators=(',', ':'))
    if body != prev:
        out['updated'] = int(time.time()); json.dump(out, open(os.path.join(ROOT, 'channel.json'), 'w'), separators=(',', ':'))
    print('channel part value %.4f on %s, trades %d, active=%s' % (value, iso(D[i]), len(trades), state['active']))

if __name__ == '__main__':
    main()
