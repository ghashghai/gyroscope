"""Liquidity / macro inputs (free, no key): FRED public CSVs + DefiLlama stablecoin total. Writes macro.json. Never fails the workflow."""
import json, time, urllib.request, csv, io, os
def get(url, to=12):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 gyroscope-radar'}), timeout=to).read().decode()
FRED = {'WALCL': 'fed_balance_sheet_mn', 'WTREGEN': 'tga_bn', 'RRPONTSYD': 'reverse_repo_bn', 'M2SL': 'm2_bn', 'DTWEXBGS': 'dollar_broad', 'DGS10': 'us10y'}
out = {'fetched': int(time.time()), 'series': {}, 'status': {}}
fails = 0
for sid, name in FRED.items():
    if fails >= 2:
        out['status'][name] = 'skipped (FRED unreachable)'; continue
    ok = False
    for url, kind in [('https://fred.stlouisfed.org/graph/fredgraph.csv?id=%s&cosd=2022-01-01' % sid, 'csv'), ('https://fred.stlouisfed.org/data/%s.txt' % sid, 'txt')]:
        try:
            raw = get(url)
            pts = []
            if kind == 'csv':
                for row in list(csv.reader(io.StringIO(raw)))[1:]:
                    try: pts.append([row[0], float(row[1])])
                    except Exception: pass
            else:
                started = False
                for ln in raw.splitlines():
                    if ln.startswith('DATE'): started = True; continue
                    if started:
                        a = ln.split()
                        try: pts.append([a[0], float(a[1])])
                        except Exception: pass
            if pts:
                out['series'][name] = pts[-900:]; out['status'][name] = 'ok %s %d, last %s' % (kind, len(pts), pts[-1][0]); ok = True; break
        except Exception as e:
            out['status'][name] = 'FAILED %s %s' % (kind, e)
    fails = 0 if ok else fails + 1
    time.sleep(1)

# ---- fallbacks when FRED is unreachable from Actions ----
import concurrent.futures as cf
def yahoo(sym, name):
    try:
        j = json.loads(get('https://query1.finance.yahoo.com/v8/finance/chart/%s?range=2y&interval=1d' % sym))
        r = j['chart']['result'][0]; ts = r['timestamp']; cl = r['indicators']['quote'][0]['close']
        pts = [[time.strftime('%Y-%m-%d', time.gmtime(t)), c] for t, c in zip(ts, cl) if c is not None]
        return name, pts, 'ok yahoo %d, last %s' % (len(pts), pts[-1][0])
    except Exception as e:
        return name, None, 'FAILED yahoo %s' % e
def nyfed_rrp():
    try:
        j = json.loads(get('https://markets.newyorkfed.org/api/rp/reverserepo/propositions/search.json?startDate=2023-01-01&endDate=%s' % time.strftime('%Y-%m-%d')))
        pts = {}
        for x in j['repo']['operations']:
            pts[x['operationDate']] = pts.get(x['operationDate'], 0) + float(x.get('totalAmtAccepted') or 0) / 1e9
        pts = sorted([[d, v] for d, v in pts.items()])
        return 'reverse_repo_bn', pts, 'ok nyfed %d, last %s' % (len(pts), pts[-1][0])
    except Exception as e:
        return 'reverse_repo_bn', None, 'FAILED nyfed %s' % e
def tga():
    try:
        j = json.loads(get('https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance?filter=account_type:eq:Treasury%20General%20Account%20(TGA)%20Closing%20Balance&sort=-record_date&page%5Bsize%5D=900&fields=record_date,open_today_bal,close_today_bal'))
        pts = sorted([[x['record_date'], float(x.get('open_today_bal') or x.get('close_today_bal')) / 1e3] for x in j['data'] if (x.get('open_today_bal') or x.get('close_today_bal'))])
        return 'tga_bn', pts, 'ok fiscaldata %d, last %s' % (len(pts), pts[-1][0])
    except Exception as e:
        return 'tga_bn', None, 'FAILED fiscaldata %s' % e
jobs = []
with cf.ThreadPoolExecutor(6) as ex:
    if 'dollar_broad' not in out['series']: jobs.append(ex.submit(yahoo, 'DX-Y.NYB', 'dollar_broad'))
    if 'us10y' not in out['series']: jobs.append(ex.submit(yahoo, '%5ETNX', 'us10y'))
    if 'reverse_repo_bn' not in out['series']: jobs.append(ex.submit(nyfed_rrp))
    if 'tga_bn' not in out['series']: jobs.append(ex.submit(tga))
    for f in jobs:
        name, pts, st = f.result()
        out['status'][name] = st
        if pts: out['series'][name] = pts[-900:]
try:
    j = json.loads(get('https://stablecoins.llama.fi/stablecoincharts/all'))
    pts = []
    for x in j:
        try: pts.append([time.strftime('%Y-%m-%d', time.gmtime(int(x['date']))), x['totalCirculatingUSD']['peggedUSD'] / 1e9])
        except Exception: pass
    out['series']['stablecoins_bn'] = pts[-900:]
    out['status']['stablecoins_bn'] = 'ok %d, last %s' % (len(pts), pts[-1][0] if pts else '-')
except Exception as e:
    out['status']['stablecoins_bn'] = 'FAILED %s' % e
json.dump(out, open('macro.json', 'w'), separators=(',', ':'))
print(out['status'])
