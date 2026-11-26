/* Siren sensor: military radar-scope panel that powers on/off live + synthesized shofar (ram's horn) blasts.
   window.Siren.update({on, why:[{t:'A'|'B'|'C', day, txt}], extra}) is called by index.html.
   Sound needs one tap per page load (browser rule). ?siren=test starts in demo mode. */
(function () {
  'use strict';
  const host = document.getElementById('siren'); if (!host) return;
  const DPR = Math.min(window.devicePixelRatio || 1, 2), TAU = Math.PI * 2;

  const css = `
#siren{margin:12px 0;display:none}
.sn-mini{position:absolute;bottom:8px;inset-inline-start:8px;z-index:3;display:flex;gap:6px;opacity:.4;transition:opacity .3s}
.sn-mini:hover,.sn-mini:active,.sn-mini:focus-within{opacity:1}
.sn-mini button{background:rgba(5,8,6,.6);color:#cfc38a;border:1px solid rgba(120,130,105,.5);border-radius:8px;padding:3px 9px;font-size:11px;font-weight:600;font-family:Tahoma,system-ui,sans-serif}
.sn-mini button.act{border-color:#d7c78a;color:#ffe9a3}
.sn{position:relative;border-radius:14px;border:2px solid #3a4136;background:linear-gradient(#0d110e,#070907);padding:10px 12px 12px;overflow:hidden;font-family:ui-monospace,Menlo,Consolas,Tahoma,monospace;box-shadow:inset 0 0 0 1px #000,inset 0 2px 10px rgba(255,255,255,.04);transition:border-color .5s,box-shadow .5s}
.sn::before{content:'';position:absolute;inset:4px;pointer-events:none;background:radial-gradient(circle,#7d8576 0 2px,transparent 2.7px) left top/10px 10px no-repeat,radial-gradient(circle,#7d8576 0 2px,transparent 2.7px) right top/10px 10px no-repeat,radial-gradient(circle,#7d8576 0 2px,transparent 2.7px) left bottom/10px 10px no-repeat,radial-gradient(circle,#7d8576 0 2px,transparent 2.7px) right bottom/10px 10px no-repeat}
.sn::after{content:'';position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,rgba(0,0,0,.2) 0 1px,transparent 1px 3px)}
.sn.on{border-color:#b13a32;animation:snb 1.1s ease-in-out infinite}
@keyframes snb{0%,100%{box-shadow:inset 0 0 0 1px #000,0 0 0 0 rgba(255,59,48,.0),inset 0 0 18px rgba(255,59,48,.10)}50%{box-shadow:inset 0 0 0 1px #000,0 0 22px 3px rgba(255,59,48,.55),inset 0 0 30px rgba(255,59,48,.25)}}
.sn-head{display:flex;align-items:center;gap:10px;position:relative;z-index:1}
.sn-head b{color:#c9d2bd;font-size:13px;letter-spacing:.5px}
.sn-head .tg{color:#6c7664;font-size:11px;direction:ltr}
.sn-state{margin-inline-start:auto;font-size:13px;color:#59634f;font-weight:700}
.sn.on .sn-state{color:#ff5a4d;animation:snt .55s steps(2,end) infinite}
.sn.demo .sn-state{color:#ffb347}
@keyframes snt{50%{opacity:.25}}
.led{flex:none;width:14px;height:14px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#59604f,#1a1d17);box-shadow:inset 0 0 3px #000}
.led.lit{background:radial-gradient(circle at 35% 30%,#ffc2bb,#ff3b30 55%,#7a0d08);box-shadow:0 0 10px 3px rgba(255,59,48,.8);animation:snl .6s ease-in-out infinite alternate}
@keyframes snl{from{opacity:.45}to{opacity:1}}
.sn-main{max-height:0;opacity:0;overflow:hidden;transition:max-height .8s ease,opacity .6s ease;position:relative;z-index:1}
.sn.on .sn-main{max-height:560px;opacity:1}
.sn-row{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-top:10px}
.sn-scope{width:168px;height:168px;flex:none;border-radius:50%}
.sn-lamps{flex:1;min-width:130px;display:grid;gap:8px}
.lamp{display:flex;align-items:center;gap:9px;font-size:13px;color:#7a846f}
.lamp.on{color:#ffb7b0}
.lamp .l{direction:ltr;font-size:11px;color:#59634f;width:14px}
.sn-why{margin:10px 0 0;padding-inline-start:20px;color:#ffd9d6;font-size:13.5px;line-height:1.8;font-family:Tahoma,system-ui,sans-serif}
.sn-note{margin-top:6px;font-size:12.5px;color:#9aa38f;font-family:Tahoma,system-ui,sans-serif;line-height:1.8}
.sn-btns{display:flex;gap:8px;margin-top:10px;position:relative;z-index:1;flex-wrap:wrap}
.sn button{background:#161b14;color:#d7c78a;border:1px solid #4a5343;border-radius:8px;padding:6px 12px;font-size:13px;font-weight:600;font-family:inherit}
.sn button.act{border-color:#d7c78a;color:#ffe9a3}
body.sn-alert::after{content:'';position:fixed;inset:0;pointer-events:none;z-index:60;box-shadow:inset 0 0 80px 8px rgba(232,60,50,.42);animation:snv 1.1s ease-in-out infinite}
@keyframes snv{0%,100%{opacity:.25}50%{opacity:1}}
`;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  host.innerHTML = `<div class="sn" id="sn">
  <div class="sn-head"><span class="led" id="snled"></span><b>حسگر آژیر</b><span class="tg">SIREN · BTC</span><span class="sn-state" id="snst">خاموش · آرامش</span></div>
  <div class="sn-main">
    <div class="sn-row"><canvas class="sn-scope" id="snsc"></canvas>
      <div class="sn-lamps">
        <div class="lamp" data-t="A"><span class="led"></span><span class="l">A</span>شتاب</div>
        <div class="lamp" data-t="B"><span class="led"></span><span class="l">B</span>خروج از روند</div>
        <div class="lamp" data-t="C"><span class="led"></span><span class="l">C</span>افت ۷ روزه</div>
      </div></div>
    <ul class="sn-why" id="snwhy"></ul><div class="sn-note" id="snnote"></div>
  </div>
</div>`;
  const heroEl = document.getElementById('hero'), mini = document.createElement('div');
  mini.className = 'sn-mini'; mini.innerHTML = '<button id="snsnd">صدا: خاموش</button><button id="sndemo">آزمایش آژیر</button>'; (heroEl || host).appendChild(mini);
  ['pointerdown', 'touchstart', 'mousedown'].forEach((ev) => mini.addEventListener(ev, (e) => e.stopPropagation()));
  const $ = (id) => document.getElementById(id), box = $('sn'), cv = $('snsc'), ctx = cv.getContext('2d'), S = 168;
  cv.width = S * DPR; cv.height = S * DPR; ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
  const SECT = { A: [.9, .66], B: [3.1, .46], C: [5.2, .78] };  // angle (rad), radius fraction of the blip per trigger
  const DEMO = { on: true, why: [{ t: 'A', day: 'آزمایشی', txt: 'نمونهٔ آزمایشی: شتاب' }, { t: 'C', day: 'آزمایشی', txt: 'نمونهٔ آزمایشی: افت ۷ روزه ۱۸٪' }], extra: '' };
  let real = { on: false, why: [], extra: '' }, demo = /[?&]siren=test/.test(location.search), on = false, power = 0, raf = 0, last = 0, soundOn = false, hideT = 0;
  const clutter = []; { let s = 7; const r = () => (s = (s * 16807) % 2147483647) / 2147483647; for (let i = 0; i < 16; i++) clutter.push([r() * TAU, .15 + r() * .8]); }

  /* ---------- radar scope ---------- */
  function draw(t) {
    ctx.clearRect(0, 0, S, S); const p = power; if (p < .01) return;
    const c = S / 2, R = c - 9, boot = p < .98 && Math.random() < .3 ? .5 : 1, why = (demo ? DEMO : real).why, act = {}; for (const w of why) act[w.t] = 1;
    ctx.save(); ctx.translate(c, c); ctx.globalAlpha = p * boot;
    // bezel ticks
    ctx.strokeStyle = 'rgba(190,200,175,.6)'; for (let i = 0; i < 72; i++) { const a = i * TAU / 72, l = i % 6 === 0 ? 7 : 3.5; ctx.lineWidth = i % 6 === 0 ? 1.6 : 1; ctx.beginPath(); ctx.moveTo(Math.cos(a) * (R + 2), Math.sin(a) * (R + 2)); ctx.lineTo(Math.cos(a) * (R + 2 + l), Math.sin(a) * (R + 2 + l)); ctx.stroke(); }
    ctx.beginPath(); ctx.arc(0, 0, R * Math.min(1, .3 + p * .7), 0, TAU); ctx.clip();
    let g = ctx.createRadialGradient(0, 0, 0, 0, 0, R); g.addColorStop(0, 'rgba(60,6,4,.95)'); g.addColorStop(1, 'rgba(14,1,1,1)'); ctx.fillStyle = g; ctx.fillRect(-R, -R, 2 * R, 2 * R);
    ctx.strokeStyle = 'rgba(255,90,80,.28)'; ctx.lineWidth = 1; for (let i = 1; i <= 3; i++) { ctx.beginPath(); ctx.arc(0, 0, R * i / 3, 0, TAU); ctx.stroke(); }
    ctx.beginPath(); ctx.moveTo(-R, 0); ctx.lineTo(R, 0); ctx.moveTo(0, -R); ctx.lineTo(0, R); ctx.stroke();
    const th = (t * 1.9) % TAU;
    for (let k = 0; k < 42; k++) { const a1 = th - k * .028, a0 = a1 - .03; ctx.fillStyle = 'rgba(255,70,60,' + (.34 * (1 - k / 42)).toFixed(3) + ')'; ctx.beginPath(); ctx.moveTo(0, 0); ctx.arc(0, 0, R, a0, a1); ctx.closePath(); ctx.fill(); }
    ctx.strokeStyle = 'rgba(255,170,160,.95)'; ctx.lineWidth = 1.6; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.cos(th) * R, Math.sin(th) * R); ctx.stroke();
    const since = (a) => { let d = (th - a) % TAU; if (d < 0) d += TAU; return d; };
    for (const [a, rf] of clutter) { const gl = Math.exp(-since(a) * 1.4); ctx.fillStyle = 'rgba(255,120,110,' + (.05 + .3 * gl).toFixed(3) + ')'; ctx.fillRect(Math.cos(a) * rf * R - 1, Math.sin(a) * rf * R - 1, 2, 2); }
    for (const k in act) {
      const [a, rf] = SECT[k], gl = Math.exp(-since(a) * .9), x = Math.cos(a) * rf * R, y = Math.sin(a) * rf * R, pr = ((t * .7 + a) % 1);
      ctx.strokeStyle = 'rgba(255,110,100,' + (.55 * (1 - pr)).toFixed(3) + ')'; ctx.lineWidth = 1.2; ctx.beginPath(); ctx.arc(x, y, 4 + pr * R * .3, 0, TAU); ctx.stroke();
      ctx.fillStyle = 'rgba(255,140,130,' + (.4 + .6 * gl).toFixed(3) + ')'; ctx.beginPath(); ctx.arc(x, y, 3 + 3.5 * gl, 0, TAU); ctx.fill();
    }
    ctx.fillStyle = 'rgba(0,0,0,.2)'; for (let y = -R; y < R; y += 3) ctx.fillRect(-R, y, 2 * R, 1);
    g = ctx.createLinearGradient(-R, -R, R * .2, R * .2); g.addColorStop(0, 'rgba(255,255,255,.09)'); g.addColorStop(1, 'rgba(255,255,255,0)'); ctx.fillStyle = g; ctx.fillRect(-R, -R, 2 * R, 2 * R);
    ctx.restore();
  }
  function loop(ts) {
    raf = requestAnimationFrame(loop); const dt = Math.min(.05, (ts - last) / 1000 || .016); last = ts;
    power += ((on ? 1 : 0) - power) * Math.min(1, dt * 3.2); draw(ts / 1000);
    if (!on && power < .01) { power = 0; ctx.clearRect(0, 0, S, S); cancelAnimationFrame(raf); raf = 0; }
  }
  const startLoop = () => { if (!raf) { last = performance.now(); raf = requestAnimationFrame(loop); } };

  /* ---------- shofar (ram's horn) synthesis ---------- */
  const Shofar = (() => {
    let ctx2 = null, master = null, verb = null, noise = null, timer = 0, buses = [];
    function init() {
      if (ctx2) return true; const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return false;
      ctx2 = new AC(); const comp = ctx2.createDynamicsCompressor(); master = ctx2.createGain(); master.gain.value = .6; master.connect(comp); comp.connect(ctx2.destination);
      verb = ctx2.createConvolver(); const len = Math.floor(ctx2.sampleRate * 2.4), b = ctx2.createBuffer(2, len, ctx2.sampleRate);
      for (let ch = 0; ch < 2; ch++) { const d = b.getChannelData(ch); for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.6); }
      verb.buffer = b; const vg = ctx2.createGain(); vg.gain.value = .38; verb.connect(vg); vg.connect(comp);
      const nb = ctx2.createBuffer(1, ctx2.sampleRate, ctx2.sampleRate), nd = nb.getChannelData(0); for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1; noise = nb;
      return true;
    }
    function note(bus, t0, dur, f0, f1) {
      const A = ctx2, osc = [['sawtooth', 1, .5, 0], ['square', 1, .2, 7], ['triangle', .5, .2, 0]], src = A.createGain(), buzz = A.createGain(); buzz.gain.value = .86;
      const lfo = A.createOscillator(), lg = A.createGain(); lfo.frequency.value = 5.3; lg.gain.value = f0 * .006; lfo.connect(lg);
      const bz = A.createOscillator(), bg = A.createGain(); bz.frequency.value = 72; bg.gain.value = .14; bz.connect(bg); bg.connect(buzz.gain);
      const all = [lfo, bz];
      for (const [type, m, gv, det] of osc) {
        const o = A.createOscillator(), g = A.createGain(); o.type = type; o.detune.value = det; g.gain.value = gv;
        o.frequency.setValueAtTime(f0 * .86 * m, t0); o.frequency.exponentialRampToValueAtTime(f0 * m, t0 + .14); o.frequency.exponentialRampToValueAtTime(f1 * m, t0 + dur);
        lg.connect(o.frequency); o.connect(g); g.connect(src); all.push(o);
      }
      const ns = A.createBufferSource(); ns.buffer = noise; ns.loop = true; const ng = A.createGain(); ng.gain.value = .05; ns.connect(ng); ng.connect(src); all.push(ns);
      src.connect(buzz);
      const env = A.createGain(), at = dur < .3 ? .025 : .07, rl = dur < .3 ? .05 : .13;
      env.gain.setValueAtTime(0, t0); env.gain.linearRampToValueAtTime(1, t0 + at); env.gain.setValueAtTime(1, t0 + Math.max(at, dur - rl)); env.gain.linearRampToValueAtTime(0, t0 + dur + .04);
      for (const [fq, q, gv] of [[520, 3.5, 1], [1150, 4, .7], [2300, 3, .3]]) { const f = A.createBiquadFilter(), g = A.createGain(); f.type = 'bandpass'; f.frequency.value = fq; f.Q.value = q; g.gain.value = gv; buzz.connect(f); f.connect(g); g.connect(env); }
      const body = A.createGain(); body.gain.value = .3; buzz.connect(body); body.connect(env);
      env.connect(bus);
      for (const o of all) { o.start(t0); o.stop(t0 + dur + .3); }
    }
    function pattern() {
      if (!ctx2) return; const A = ctx2, bus = A.createGain(); bus.connect(master); bus.connect(verb); buses.push(bus); const T = A.currentTime + .05;
      note(bus, T, 2.3, 300, 322);                                               // tekiah
      for (let i = 0; i < 3; i++) note(bus, T + 3.1 + i * .82, .7, 300 + i * 7, 330);   // shevarim
      for (let i = 0; i < 9; i++) note(bus, T + 6.2 + i * .17, .13, 330, 345);          // teruah
      note(bus, T + 8.5, 3.4, 300, 338);                                         // tekiah gedolah
      setTimeout(() => { buses = buses.filter((x) => x !== bus); try { bus.disconnect(); } catch (_) { } }, 14000);
    }
    return {
      enable() { if (!init()) return false; if (ctx2.state === 'suspended') ctx2.resume(); const bus = ctx2.createGain(); bus.connect(master); bus.connect(verb); buses.push(bus); note(bus, ctx2.currentTime + .05, 1.7, 300, 318); return true; },
      loop() { if (!ctx2) return; this.stopLoop(true); pattern(); timer = setInterval(pattern, 15500); },
      stopLoop(keep) { clearInterval(timer); timer = 0; if (keep) return; if (ctx2) for (const b of buses) { try { b.gain.cancelScheduledValues(ctx2.currentTime); b.gain.setTargetAtTime(0, ctx2.currentTime, .06); } catch (_) { } } },
    };
  })();

  /* ---------- state ---------- */
  function apply() {
    const s = demo ? DEMO : real, next = !!(demo || real.on);
    box.classList.toggle('demo', demo);
    box.querySelectorAll('.lamp').forEach((l) => { const hit = s.why.some((w) => w.t === l.dataset.t); l.classList.toggle('on', hit); l.firstChild.classList.toggle('lit', hit); });
    $('snwhy').innerHTML = s.why.map((w) => '<li>' + w.txt + ' <span style="color:#8c9582">(' + w.day + ')</span></li>').join('');
    $('snnote').innerHTML = (s.extra || '') + (demo ? '<div>حالت آزمایشی است؛ واقعی نیست.</div>' : '<div>پیش‌بینی نیست. در آزمون، در روزهای آژیر احتمال افت ۲۰٪ بیشتر ظرف ۳۰ روز ۳۳٪ بود، در برابر ۲۰٪ در حالت عادی. فقط بیت‌کوین سنجیده شده.</div>');
    $('snst').textContent = next ? (demo ? 'آزمایشی · ALERT' : 'خطر · ALERT') : 'خاموش · آرامش';
    $('snled').classList.toggle('lit', next);
    $('sndemo').textContent = demo ? 'پایان آزمایش' : 'آزمایش آژیر'; $('sndemo').classList.toggle('act', demo);
    if (next !== on) {
      on = next; clearTimeout(hideT); document.body.classList.toggle('sn-alert', on);
      if (on) { host.style.display = 'block'; void host.offsetHeight; box.classList.add('on'); startLoop(); }
      else { box.classList.remove('on'); hideT = setTimeout(() => { if (!on) host.style.display = 'none'; }, 1000); }
      if (window.Scene && Scene.setAlert) Scene.setAlert(on);
      if (soundOn) on ? Shofar.loop() : Shofar.stopLoop();
    }
  }
  $('snsnd').onclick = () => {
    if (!soundOn) { if (!Shofar.enable()) { $('snsnd').textContent = 'صدا در این مرورگر نیست'; return; } soundOn = true; $('snsnd').textContent = 'صدا: روشن'; $('snsnd').classList.add('act'); if (on) setTimeout(() => Shofar.loop(), 2200); }
    else { soundOn = false; Shofar.stopLoop(); $('snsnd').textContent = 'صدا: خاموش'; $('snsnd').classList.remove('act'); }
  };
  $('sndemo').onclick = () => { demo = !demo; apply(); };
  window.Siren = { update(s) { real = s || real; apply(); } };
  apply();
})();
