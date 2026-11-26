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

## Siren + scene (2026-11-26)
- Page layout (index.html): hero scene (`#hero`, scene.js) -> siren sensor panel (`#siren`, siren.js) -> update button -> cards. Scripts are loaded as `scene.js?v=27` and `siren.js?v=28`: bump v when changing them (phone cache).
- **Siren logic** is `sirenState(S, aux)` in index.html (BTC only). Trigger on any of the last 3 closed days: (A) parabola: dist150 >100% & 30d-vol percentile >85%; (B) fresh SMA150 exit (close below SMA150, was above within 3 days before); (C) 7-day fall >=15%. Liquidation >=3x 30d mean is only an extra line. It calls `Siren.update({on, why, extra})`. `refreshSiren()` re-reads ohlcv/liq/price every 15 min so the sensor stays live without reload.
- **Siren look (siren.js)**: military sensor panel. Off = completely hidden (`#siren` display:none; only a faint sound/demo pill sits inside the hero). On = panel shows and expands, red radar scope with sweep, blips per trigger (A 50deg, B 177deg, C 298deg), 3 lamps blinking, reasons list, red pulsing screen edge (`body.sn-alert`), scene turns red-tinted (`Scene.setAlert`). Pill buttons (in hero): sound toggle, demo toggle. `?siren=test` starts in demo mode.
- **Sound**: WebAudio synthesized shofar (saw+square+triangle through 3 bandpass formants, lip-buzz AM, vibrato, noise breath, synthetic reverb). Pattern tekiah - shevarim - teruah - tekiah gedolah, repeated every 15.5 s while on. Browsers need one tap on the sound button per page load; no push/notifications (user declined).
- **Scene (scene.js)**: no libs. WebGL fragment shader nebula (domain-warped fbm; phosphor blue/green gas, dark stone-like dense clouds with ridged rock grain, anisotropic quartz-silk threads, glints, faint far spiral galaxy, no sun), canvas-2D gold armillary gyroscope (3 gimbals + spinning rotor, metal shading reflecting the blue/green environment), floating quartz crystals, silk filaments, dust. Drag with a finger to tilt. Falls back to a CSS gradient without WebGL; honors prefers-reduced-motion. Verified in headless Chrome (SwiftShader), not on a real phone GPU: if it is slow, lower `gs` in `resize()`.
- Backtest (BTC, from day 200, no look-ahead): any trigger on 8.1% of days; P(-20% further within 30d) = 33% vs 20% base. A 45% (5 episodes, hypothesis), C 33% (65), B 26% (39, weak, kept as the exit rule). Replay fires on 2018-01-17, 2020-03-12, 2021-05-19, 2021-12-04, 2022-06-13, 2022-11-09, 2025-10-11. Today (2026-11-24 close): peace.
- Not yet: siren for ETH/BNB/SUI (A is BTC-calibrated; B/C untested on alts).

## Command section "فرمان" (2026-11-26, first card in the output)
- Code in index.html: `sirenFlags` (A/B/C per day, shared by `sirenState`), `ladderLevels()` (the 6 ladder prices; `partsCard` uses it too, needs `window.__rp` from `mvrvCard`, so mvrvCard runs first), `analogSet`, `analogStats`, `commandCard`, `drawCommand` (canvas `cv4`).
- Brain = the user's own rules, not the simulation: target 0% BTC/100% USDT when close < SMA150 or siren A; 6 conditional ladder buys; part 7 only after a close above SMA150. The card shows next conditional order, a table of all orders, and the analog evidence beside each ladder level.
- Analog engine: 12 most similar past days since 2013 (features: log dist to SMA150, 7d and 30d log return, drawdown from 1y high, 30d vol; weights 1.2/1/1/1.2/.8; at least 30 days apart; forward 90 days). Pool: days with a siren trigger in the last 3 days if the siren is on, otherwise days on the same side of SMA150 as today. Forward paths are rescaled to today's price and drawn with ladder lines, SMA150, median and 25-75% band.
- **Honest calibration (only past data per day):** 51 siren episodes since 2016: realized P(-20% within 90d) 43% = analog average 43%, but rank correlation of analog-predicted vs realized min = -0.19 (no skill; high-P20 episodes hit 38%, low-P20 53%). Quiet mode (74 samples): predicted 47%, realized 35%, rank corr -0.27. So the fan is a base-rate picture, not a forecast; do not tune orders from it. This note is printed in the card.
- Today (2026-11-25): out of market (-18% vs SMA150 72.9k), siren off, next order P1 57,356 (83% of analogs touched it within 90d, median day 9), median analog low ~49.3k around day 20. Replays on 2018-01-17, 2021-05-19, 2022-06-13: analogs under-warned (analog median min +2/-14/-7% vs real -41/-19/-16%).
- Ideas not built: analog selection with liquidation rate, Tether flows, volume (the user asked earlier; only price features used so far); a different matching method to see if any skill appears.

## Pending / next
1. Siren for ETH/BNB/SUI after testing them (no push alerts: user declined).
2. Ladder for ETH/BNB/SUI (no MVRV: use trend + Fibonacci).
3. Regenerate Coinalyze key -> repo Secret.
4. Hourly chart page using ohlcv1h.json / liq1h.json (history accumulates from ~Sept 2026).
5. Look for exchange USDT flow source (not found free).
