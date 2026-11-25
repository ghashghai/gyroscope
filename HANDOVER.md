# Gyroscope radar — handover notes (2026-11-25)

Live page: https://ghashghai.github.io/gyroscope/  (use ?v=N to bypass cache)
Owner: Persian speaker, phone only, wants slow step-by-step guidance, copyable text in code blocks, no file downloads.

## Files
- index.html — whole page (Persian RTL, no libs). Cards: coin status (BTC/ETH/BNB/SUI), BACKTEST static card, MVRV card, seven-parts ladder, swing map (peaks, crash types), current-cycle Fibonacci chart, future-path simulator (3 modes), parabola alarm, today's crash type.
- scripts/fetch.py + .github/workflows/liq.yml — Actions every 6h; fetches Coinalyze (liq, oi, funding, lsr, ohlcv daily + ohlcv1h + liq1h), CoinMetrics btc.csv (price.json, onchain.json: MVRV, exchange flows), usdt_eth/usdt_trx.json (stale, ends 2026-05), DefiLlama usdt_supply.json (fresh). Push to main triggers it. Always `git pull --rebase origin main` before push (bot commits data).
- Coinalyze key is public in the workflow (should be regenerated and moved to repo Secrets).

## Findings (real data, in-sample, small samples — not predictions)
- Only robust rule: close vs SMA150 (exit below, enter above). Median 49% of 16 crashes (>=40%) avoided; ~87% of rallies captured (7 true entries).
- Price-only indicators (RSI, %R, MACD, vote-consensus) add nothing; they are correlated.
- MVRV <0.8: P(no new big drop in 90d and +20% in 180d)=74% vs 24% base (5 episodes). RSI<20: 18% (worse than chance). First MVRV-ladder buys were 30–47% early in 3 of 4 cycles.
- Sudden crashes (<=14d to -30%) follow parabolic spikes (dist150 >100% & vol pct >85%: 71% chance of -20% in 30d vs 15% base; only 3 episodes). Medium/slow crashes: no precursor found.
- Liquidation spikes (ratio>=3 vs 30d mean) happen on 91 of 1472 days and do not predict crashes. 73% of liquidated money (15/30d, BTC/ETH/BNB/SUI) was longs.
- Exchange flow (BTC into exchanges) has a tilt alone, adds nothing to the trend rule. Exchange USDT flow requires paid CryptoQuant/Glassnode; free only USDT total supply (174B now, -4.4%/30d, peaked 190B on 2026-05-20).
- Fibonacci = symbolic map layer only (user's wish); past 3 cycle bottoms were at 0.80–0.85 retracement, not 0.618.
- Today (2026-11-25): BTC ~59.2k, below SMA150 (~72.9k) -> red/out. Est. MVRV ~1.1 (realized price ~54.2k). Ladder: 57.4k, 54.2k, 43.4k, 42k, 39.1k, 38.0k, reserve above SMA150.

## Siren (done 2026-11-26, page-only, BTC only)
- `sirenCard(S, aux)` in index.html, rendered first in `run()`. Returns '' in peace (nothing shown); red pulsing banner when any trigger fired on one of the last 3 closed days: (A) parabola: dist150 >100% & 30d-vol percentile >85%; (B) fresh SMA150 exit: close below SMA150 and was above within the 3 days before; (C) 7-day fall >=15%. Liquidation >=3x the 30d mean is shown only as an extra line, never triggers.
- `?siren=test` on the page URL forces a sample banner (to see how it looks).
- Backtest (BTC, from day 200, no look-ahead): any trigger on 8.1% of days; P(-20% further within 30d) = 33% vs 20% base. By trigger: A 45% (5 episodes, hypothesis), C 33% (65 episodes), B 26% (39 episodes, weak, kept because it is the exit rule). Replay: fires on 2018-01-17, 2020-03-12, 2021-05-19, 2021-12-04, 2022-06-13, 2022-11-09, 2025-10-11. Today (2026-11-24 close, 59.8k): peace (below SMA150 for 13 days, 7d change -7.9%; C fired once ~5 days ago, out of the 3-day window).
- Not yet: ETH/BNB/SUI (A is BTC-calibrated, B/C untested on alts); push alert (idea: Actions opens a GitHub Issue when red, untested).

## Pending / next
1. Siren push alert (GitHub Issue from Actions when red) and siren for ETH/BNB/SUI after testing them.
2. Ladder for ETH/BNB/SUI (no MVRV: use trend + Fibonacci).
3. Regenerate Coinalyze key -> repo Secret.
4. Hourly chart page using ohlcv1h.json / liq1h.json (history accumulates from ~Sept 2026).
5. Look for exchange USDT flow source (not found free).
