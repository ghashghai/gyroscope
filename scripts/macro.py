"""Liquidity / macro inputs (free, no key): FRED public CSVs + DefiLlama stablecoin total. Writes macro.json. Never fails the workflow."""
import json, time, urllib.request, csv, io, os
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'gyroscope-radar'}), timeout=40).read().decode()
FRED = {'WALCL': 'fed_balance_sheet_mn', 'WTREGEN': 'tga_bn', 'RRPONTSYD': 'reverse_repo_bn', 'M2SL': 'm2_bn', 'DTWEXBGS': 'dollar_broad', 'DGS10': 'us10y'}
out = {'fetched': int(time.time()), 'series': {}, 'status': {}}
for sid, name in FRED.items():
    try:
        rows = list(csv.reader(io.StringIO(get('https://fred.stlouisfed.org/graph/fredgraph.csv?id=' + sid))))[1:]
        pts = []
        for d, v in rows:
            try: pts.append([d, float(v)])
            except Exception: pass
        out['series'][name] = pts[-900:]
        out['status'][name] = 'ok %d, last %s' % (len(pts), pts[-1][0] if pts else '-')
    except Exception as e:
        out['status'][name] = 'FAILED %s' % e
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
