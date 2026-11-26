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
