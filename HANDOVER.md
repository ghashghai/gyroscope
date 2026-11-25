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

## Pending / next
1. Siren ("آژیر"): user wants nothing shown in peace, red in danger. Planned triggers: parabola alarm on, fresh SMA150 exit, 7-day fall >=15%; liquidation shock only as extra reason. Page-only; push alert idea: Actions creates a GitHub Issue when red (untested).
2. Ladder for ETH/BNB/SUI (no MVRV: use trend + Fibonacci).
3. Regenerate Coinalyze key -> repo Secret.
4. Hourly chart page using ohlcv1h.json / liq1h.json (history accumulates from ~Sept 2026).
5. Look for exchange USDT flow source (not found free).
