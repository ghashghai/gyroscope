import json, os, sys, time, urllib.request, urllib.error

KEY = os.environ.get('KEY', '')
SYMS = 'BTCUSDT_PERP.A,ETHUSDT_PERP.A,BNBUSDT_PERP.A,SUIUSDT_PERP.A'
NOW = int(time.time())
meta = {'fetched': NOW, 'status': {}}


def get(url, tries=3):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'gyroscope-radar'})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = 'HTTP %s' % e.code
            if e.code == 429:
                time.sleep(20)
            elif e.code in (400, 401, 403, 404):
                break
        except Exception as e:  # network / json
            last = str(e)[:80]
        time.sleep(5)
    raise RuntimeError(last)


def merge_history(path, new_list):
    """keep everything already stored; add/overwrite by (symbol, t)."""
    old = {}
    if os.path.exists(path):
        try:
            for s in json.load(open(path))['data']:
                old[s['symbol']] = {h['t']: h for h in s.get('history', [])}
        except Exception:
            pass
    for s in new_list:
        m = old.setdefault(s['symbol'], {})
        for h in s.get('history', []):
            m[h['t']] = h
    data = [{'symbol': k, 'history': [v[t] for t in sorted(v)]} for k, v in sorted(old.items())]
    json.dump({'fetched': NOW, 'data': data}, open(path, 'w'), separators=(',', ':'))
    return {k: len(v) for k, v in old.items()}


endpoints = [
    ('liq.json', 'liquidation-history', '&convert_to_usd=true'),
    ('oi.json', 'open-interest-history', '&convert_to_usd=true'),
    ('funding.json', 'funding-rate-history', ''),
    ('lsr.json', 'long-short-ratio-history', ''),
    ('ohlcv.json', 'ohlcv-history', ''),
]
for fname, ep, extra in endpoints:
    url = 'https://api.coinalyze.net/v1/%s?symbols=%s&interval=daily&from=1262304000&to=%d%s&api_key=%s' % (ep, SYMS, NOW, extra, KEY)
    try:
        j = get(url)
        assert isinstance(j, list) and j, 'empty'
        meta['status'][ep] = merge_history(fname, j)
    except Exception as e:
        meta['status'][ep] = 'FAILED: %s' % e
    time.sleep(3)


# hourly candles + hourly liquidations (history accumulates in the repo)
for fname, ep, extra in [('ohlcv1h.json', 'ohlcv-history', ''), ('liq1h.json', 'liquidation-history', '&convert_to_usd=true')]:
    url = 'https://api.coinalyze.net/v1/%s?symbols=%s&interval=1hour&from=%d&to=%d%s&api_key=%s' % (ep, SYMS, NOW - 80 * 86400, NOW, extra, KEY)
    try:
        j = get(url)
        assert isinstance(j, list) and j, 'empty'
        meta['status'][fname] = merge_history(fname, j)
    except Exception as e:
        meta['status'][fname] = 'FAILED: %s' % e
    time.sleep(3)

# full BTC price history 2010..today: CoinMetrics community CSV (close only), served from GitHub
try:
    import csv, io
    raw = urllib.request.urlopen(urllib.request.Request('https://raw.githubusercontent.com/coinmetrics/data/master/csv/btc.csv', headers={'User-Agent': 'gyroscope-radar'}), timeout=120).read().decode()
    rd = csv.DictReader(io.StringIO(raw))
    cols = rd.fieldnames
    volcol = next((c for c in cols if 'volume_reported_spot_usd_1d' in c), None)
    out = []
    for r in rd:
        try:
            c = float(r['PriceUSD'])
        except Exception:
            continue
        if c <= 0:
            continue
        ts = int(time.mktime(time.strptime(r['time'][:10], '%Y-%m-%d'))) - time.timezone
        v = None
        if volcol and r.get(volcol):
            try: v = float(r[volcol])
            except Exception: v = None
        out.append([ts, c, v])
    json.dump({'fetched': NOW, 'cols': ['t', 'c', 'v'], 'rows': out}, open('price.json', 'w'), separators=(',', ':'))
    meta['status']['price'] = '%d rows, %s .. %s, volcol=%s' % (len(out), time.strftime('%Y-%m-%d', time.gmtime(out[0][0])), time.strftime('%Y-%m-%d', time.gmtime(out[-1][0])), volcol)
except Exception as e:
    meta['status']['price'] = 'FAILED: %s' % e

json.dump(meta, open('meta.json', 'w'), indent=1)
print(json.dumps(meta, indent=1))
