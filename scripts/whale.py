"""Whale watch: balances of public, well-known exchange cold wallets from mempool.space (free, no key).
Appends a snapshot to whale.json every run. Labels are public attributions, not guaranteed. Never fails the workflow."""
import json, time, urllib.request, os
WALLETS = [
    ('Binance (cold 1)', '34xp4vRoCGJym3xR7yCVPFHoCNxv4Twseo'),
    ('Binance (cold 2)', '3JZq4atUahhuA9rLhXLMhhTo133J9rF97j'),
    ('Bitfinex (cold)', 'bc1qgdjqv0av3q56jvd82tkdjpy7gdp9ut8tlqmgrpmv24sq90ecnvqqjwvw97'),
]
def get(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'gyroscope-radar'}), timeout=30).read().decode())
snap = {'t': int(time.time()), 'w': {}}
err = []
for name, a in WALLETS:
    try:
        j = get('https://mempool.space/api/address/' + a)
        c, m = j['chain_stats'], j.get('mempool_stats', {'funded_txo_sum': 0, 'spent_txo_sum': 0})
        bal = (c['funded_txo_sum'] - c['spent_txo_sum'] + m['funded_txo_sum'] - m['spent_txo_sum']) / 1e8
        snap['w'][name] = round(bal, 4)
    except Exception as e:
        err.append('%s: %s' % (name, e))
    time.sleep(1.5)
# latest-block size hint: total BTC moved in the tip block is not cheap to get; keep only wallets.
try:
    h = json.load(open('whale.json')) if os.path.exists('whale.json') else {'hist': []}
except Exception:
    h = {'hist': []}
if snap['w']:
    h['hist'].append(snap)
h['hist'] = h['hist'][-1500:]
h['wallets'] = [n for n, _ in WALLETS]
h['last_status'] = 'ok %d/%d' % (len(snap['w']), len(WALLETS)) + ((' | ' + '; '.join(err)) if err else '')
json.dump(h, open('whale.json', 'w'), separators=(',', ':'))
print(h['last_status'])
