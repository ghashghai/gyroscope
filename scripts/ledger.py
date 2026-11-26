"""Live ledger (دفتر ثبت زنده). Once per closed day, freezes the radar's indicator readings for BTC from real repo data,
then later fills in what actually happened (7/30/90 days). Rows are never rewritten after creation except the outcome fields.
Rule version RV is stored in every row; if rules change, bump RV (old rows keep their own version)."""
import json, os, time, statistics
RV = 2
# RV2 cutoffs = terciles of BTC history (funding/LSR since 2020-22, vol since 2010, volume since 2018), measured 2026-11-26. In-sample => optimistic; the live ledger is the real test. Do not change without bumping RV.
FUND_LO, FUND_HI = 0.0045749, 0.0094763
LSR_LO, LSR_HI = 54.64, 64.63
VOL_LO, VOL_HI = 0.0245326, 0.0369433
VOLR_LO = 0.835994
DAY = 86400

def load(f):
    return json.load(open(f))

def sym(j, name):
    for s in j['data']:
        if s['symbol'].startswith(name + 'USDT'):
            return s['history']
    return []

def sma(a, n, i):
    return sum(a[i - n + 1:i + 1]) / n if i >= n - 1 else None

def readings(day, C, D, liq, fund, lsr, ohl, whale, oi={}, usd={}):
    """all inputs are values up to and including `day` (closed). No look-ahead."""
    i = D.index(day)
    c = C[i]
    s150, s21 = sma(C, 150, i), sma(C, 21, i)
    r = {'close': c, 'sma150': s150, 'sma21': s21}
    r['dist150'] = c / s150 - 1 if s150 else None
    r['ret7'] = c / C[i - 7] - 1 if i >= 7 else None
    r['ret30'] = c / C[i - 30] - 1 if i >= 30 else None
    # siren A/B/C as in index.html (A needs vol percentile over history)
    A = B = Cc = 0
    if i >= 200:
        lr = [0.0] + [__import__('math').log(C[k] / C[k - 1]) for k in range(1, len(C))]
        def sd(k):
            w = lr[k - 29:k + 1]; m = sum(w) / 30
            return (sum((x - m) ** 2 for x in w) / 29) ** .5
        for k in range(i - 2, i + 1):
            sk = sma(C, 150, k)
            if sk and C[k] / sk - 1 > 1:
                v = sd(k); lo = tot = 0
                for j in range(200, k + 1):
                    tot += 1; lo += sd(j) < v
                if tot and lo / tot > .85: A = 1
            if sk and C[k] < sk:
                for j in range(k - 3, k):
                    sj = sma(C, 150, j)
                    if sj and C[j] >= sj: B = 1; break
            if C[k] / C[k - 7] - 1 <= -.15: Cc = 1
    r['sirenA'], r['sirenB'], r['sirenC'] = A, B, Cc
    # positioning: 30d liquidation long share, 7d mean funding, latest long-account %
    ld = [liq[d] for d in range(day - 29, day + 1) if d in liq]
    if len(ld) >= 24:
        l = sum(x[0] for x in ld); s = sum(x[1] for x in ld); r['liq_long_share30'] = l / (l + s) if l + s else None
    else:
        r['liq_long_share30'] = None
    fv = [fund[d] for d in range(day - 6, day + 1) if d in fund and fund[d] != 0]
    r['funding7'] = sum(fv) / len(fv) if len(fv) >= 4 else None
    r['lsr_long_pct'] = lsr.get(day)
    # flow proxy: taker-buy share and mean trade size, 7d
    ov = [ohl[d] for d in range(day - 6, day + 1) if d in ohl]
    if len(ov) == 7:
        v = sum(x[0] for x in ov); r['taker_buy7'] = sum(x[1] for x in ov) / v; r['avg_trade7'] = v / sum(x[2] for x in ov)
    else:
        r['taker_buy7'] = r['avg_trade7'] = None
    r['whale_cold_total'] = whale
    import math
    if i >= 365: r['dd_1y_high'] = c / max(C[i - 364:i + 1]) - 1
    r['dist21'] = c / s21 - 1 if s21 else None
    if i >= 30:
        w = [math.log(C[k] / C[k - 1]) for k in range(i - 29, i + 1)]; m = sum(w) / 30
        r['vol30'] = (sum((x - m) ** 2 for x in w) / 29) ** .5
    else:
        r['vol30'] = None
    ob = [ohl[d] for d in range(day - 89, day + 1) if d in ohl]
    r['volume_ratio7_90'] = (sum(x[0] for x in ob[-7:]) / 7) / (sum(x[0] for x in ob) / len(ob)) if len(ob) >= 80 else None
    r['oi_chg30'] = (oi[day] / oi[day - 30] - 1) if day in oi and day - 30 in oi and oi[day - 30] > 0 else None
    r['usdt_supply_chg30'] = (usd[day] / usd[day - 30] - 1) if day in usd and day - 30 in usd and usd[day - 30] > 0 else None
    # votes (+1 supports holding, -1 warns, 0 neutral) -- rule version RV
    v = {}
    v['trend'] = None if s150 is None else (1 if c >= s150 else -1)
    v['siren'] = -1 if (A or B or Cc) else 0
    v['momentum'] = None if r['ret30'] is None else (-1 if r['ret30'] <= -.15 else (1 if r['ret30'] >= .10 else 0))
    # group votes: independent information groups, each -1/0/+1
    g = {}
    pr = (v['trend'] or 0) + (v['momentum'] if (v['momentum'] or 0) < 0 else 0)
    g['price'] = 1 if pr > 0 else (-1 if pr < 0 else 0)
    lev = 0
    fv7, lsv = r['funding7'], r['lsr_long_pct']
    if fv7 is not None: lev += -1 if fv7 >= FUND_HI else (1 if fv7 <= FUND_LO else 0)
    if lsv is not None: lev += -1 if lsv >= LSR_HI else (1 if lsv <= LSR_LO else 0)
    g['leverage'] = None if (fv7 is None and lsv is None) else (1 if lev > 0 else (-1 if lev < 0 else 0))
    vo = r['vol30']
    g['volatility'] = None if vo is None else (-1 if vo >= VOL_HI else (1 if vo <= VOL_LO else 0))
    vr = r['volume_ratio7_90']
    g['participation'] = None if vr is None else (-1 if vr <= VOLR_LO else 0)
    r['groups'] = g
    gs = [x for x in g.values() if x is not None]
    r['gscore'] = sum(gs) if gs else None
    # crowd (liquidation long share) has NO vote: in-sample its sign looked opposite to the naive reading (forced selling preceded rebounds, 3 episodes). Raw value is stored; sign to be judged on live data.
    r['votes'] = v
    vs = [x for x in v.values() if x is not None]
    r['score'] = sum(vs) if vs else None
    return r

def build():
    ohlcv = load('ohlcv.json'); H = sym(ohlcv, 'BTC')
    today = int(time.time()) // DAY
    D = [h['t'] // DAY for h in H if h['t'] // DAY < today]
    C = [h['c'] for h in H if h['t'] // DAY < today]
    liq = {h['t'] // DAY: (float(h['l']), float(h['s'])) for h in sym(load('liq.json'), 'BTC')}
    fund = {h['t'] // DAY: float(h['c']) for h in sym(load('funding.json'), 'BTC')}
    lsr = {h['t'] // DAY: float(h['l']) for h in sym(load('lsr.json'), 'BTC')}
    ohl = {h['t'] // DAY: (h['v'], h['bv'], h['tx']) for h in H if h.get('tx')}
    oi = {h['t'] // DAY: float(h['c']) for h in sym(load('oi.json'), 'BTC')}
    usd = {}
    try:
        usd = {r[0] // DAY: r[1] for r in load('usdt_supply.json')['rows']}
    except Exception:
        pass
    return D, C, liq, fund, lsr, ohl, oi, usd

def outcomes(row_day, D, C):
    if row_day not in D: return {}
    i = D.index(row_day); o = {}
    for n in (7, 30, 90):
        if i + n < len(C):
            o['fwd%d' % n] = C[i + n] / C[i] - 1
            o['min%d' % n] = min(C[i + 1:i + n + 1]) / C[i] - 1
    return o

def main():
    D, C, liq, fund, lsr, ohl, oi, usd = build()
    L = json.load(open('ledger.json')) if os.path.exists('ledger.json') else {'rv_note': 'rows are frozen when first written; only outcome fields (fwd*/min*) are filled later', 'rows': []}
    have = {r['day'] for r in L['rows']}
    last = D[-1]
    whale = None
    try:
        w = load('whale.json')['hist'][-1]['w']; whale = round(sum(w.values()), 2)
    except Exception:
        pass
    if last not in have:
        row = {'day': last, 'rv': RV, 'live': True, 'written': int(time.time())}
        row.update(readings(last, C, D, liq, fund, lsr, ohl, whale, oi, usd))
        L['rows'].append(row)
    for r in L['rows']:
        r.update(outcomes(r['day'], D, C))
    json.dump(L, open('ledger.json', 'w'), separators=(',', ':'))
    print('ledger rows', len(L['rows']), 'last', last)

if __name__ == '__main__':
    main()
