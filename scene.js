/* Gyroscope scene: deep-space phosphor nebula (WebGL) + gold armillary gyroscope + quartz crystals (canvas 2D).
   No libraries. Falls back to a CSS gradient if WebGL is missing. window.Scene.setAlert(bool) tints the scene red. */
(function () {
  'use strict';
  const hero = document.getElementById('hero'); if (!hero) return;
  const cg = document.getElementById('gl'), cf = document.getElementById('fx'), fx = cf.getContext('2d');
  const reduce = !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  const DPR = Math.min(window.devicePixelRatio || 1, 2);
  /* Quality levels (LV 0 best .. 3 lightest). The frame governor in frame() measures real frame time on this device and
     steps down if it is slow; the level is remembered for 3 days. ?q=0..3 forces a level for testing (governor off). */
  const GS = [Math.min(.75, DPR * .45), .5, .36, .26];
  let LV = 0, forced = false;
  try { const s = JSON.parse(localStorage.getItem('gyroQ') || 'null'); if (s && s.lv >= 0 && s.lv <= 3 && Date.now() - s.t < 3 * 864e5) LV = s.lv | 0; } catch (e) { }
  try { const m = /[?&]q=([0-3])(?!\d)/.exec(location.search); if (m) { LV = +m[1]; forced = true; } } catch (e) { }
  let W = 360, H = 320, alertT = 0, alertK = 0, yaw = 0.5, pitch = -0.32, vy = 0, vp = 0, drag = false, px = 0, py = 0, visible = true;
  const T0 = Math.random() * 1000;

  /* ---------- nebula shader ---------- */
  const FS = `
#ifdef GL_FRAGMENT_PRECISION_HIGH
precision highp float;
#else
precision mediump float;
#endif
uniform vec2 uRes; uniform float uTime; uniform float uAlert; uniform vec2 uCam;
float hash(vec2 p){ p=fract(p*vec2(123.34,456.21)); p+=dot(p,p+45.32); return fract(p.x*p.y); }
float noise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f);
  return mix(mix(hash(i),hash(i+vec2(1.,0.)),f.x), mix(hash(i+vec2(0.,1.)),hash(i+vec2(1.,1.)),f.x), f.y); }
float fbm(vec2 p){ float v=0., a=.5; mat2 m=mat2(1.6,1.2,-1.2,1.6); for(int i=0;i<5;i++){ v+=a*noise(p); p=m*p; a*=.5; } return v; }
float ridge(vec2 p){ float v=0., a=.5; mat2 m=mat2(1.7,1.1,-1.1,1.7); for(int i=0;i<4;i++){ v+=a*(1.-abs(noise(p)*2.-1.)); p=m*p; a*=.5; } return v; }
void main(){
  vec2 uv=(gl_FragCoord.xy-.5*uRes)/min(uRes.x,uRes.y);
  float t=uTime;
  vec2 p=uv*2.3+uCam*.18+vec2(t*.010,-t*.006);
  vec2 q=vec2(fbm(p+vec2(0.,t*.02)), fbm(p+vec2(5.2,1.3)));
  vec2 r=vec2(fbm(p+3.*q+vec2(1.7,9.2)+t*.015), fbm(p+3.*q+vec2(8.3,2.8)-t*.012));
  float f=fbm(p+3.*r);
  float dens=smoothstep(.34,.86,f);
  float stone=ridge(p*3.4+r*2.2);
  float rock=dens*(.55+.95*pow(stone,2.));
  vec3 deep=vec3(.004,.010,.030);
  vec3 blue=vec3(.05,.30,1.0), cyan=vec3(.10,.85,1.0), green=vec3(.30,1.0,.40);
  float gmix=smoothstep(.35,.75,fbm(p*.8+r*1.5+7.));
  vec3 gas=mix(blue,green,gmix);
  vec3 col=deep;
  float haze=fbm(p*.7+q*2.)*.9;
  col+=gas*haze*haze*.36;                                   // gaseous phosphorus glow
  col=mix(col,vec3(.006,.018,.045),dens*.85);                // dense stone-like body
  float edge=smoothstep(.0,.35,dens)*(1.-smoothstep(.35,.9,dens));
  col+=mix(blue,cyan,stone)*rock*.5*(.4+edge*1.7);          // lit rocky ridges
  col+=green*gmix*edge*.55*stone;                           // green phosphor on the edges
  float ang=.9+1.2*q.x;
  vec2 dir=vec2(cos(ang),sin(ang)), per=vec2(-dir.y,dir.x);
  float silk=fbm(vec2(dot(p,dir)*.9,dot(p,per)*22.)+vec2(0.,t*.05));
  silk=pow(smoothstep(.55,.9,silk),3.);
  float sm=smoothstep(.25,.6,f)*(1.-.5*dens);
  float shimmer=.65+.35*sin(t*1.7+f*18.+p.x*6.);
  col+=vec3(.75,.95,1.)*silk*sm*shimmer*.95;                // quartz silk threads
  col+=vec3(.3,1.,.7)*silk*silk*sm*.25*gmix;
  // distant spiral galaxy (no sun anywhere)
  vec2 gc=uv-vec2(-.62,.27); gc=mat2(.8,.6,-.6,.8)*gc; gc.y*=2.6; float gr=length(gc);
  float arms=.5+.5*cos(atan(gc.y,gc.x)*2.-log(gr+.02)*7.+t*.02);
  col+=vec3(.40,.60,1.)*exp(-gr*9.)*(.45+.8*arms)*.5+vec3(.7,.85,1.)*exp(-gr*45.)*.35;
  // stars, hidden behind dense cloud
  float st=0.;
  for(int s=0;s<3;s++){ float sc=70.*pow(1.7,float(s)); vec2 cp=uv*sc+float(s)*17.3; vec2 ci=floor(cp), cf=fract(cp)-.5;
    float h=hash(ci); st+=step(.986,h)*smoothstep(.32,.0,length(cf))*(.35+.65*h)*(.6+.4*sin(t*(1.+h*3.)+h*40.)); }
  col+=vec3(.7,.85,1.)*st*.8*(1.-dens*.92);
  // crystal glints
  vec2 gp=uv*125.; vec2 gi=floor(gp), gf=fract(gp)-.5; float gh=hash(gi+3.7);
  float tw=step(.982,gh)*smoothstep(.5,.0,length(gf))*(.5+.5*sin(t*(2.+gh*4.)+gh*50.));
  col+=vec3(.8,1.,1.)*tw*(.15+rock*1.6+silk*sm*2.);
  col=mix(col,col*vec3(1.4,.42,.42)+vec3(.05,0.,0.),uAlert*.55*(.65+.35*sin(t*6.)));
  col*=1.-.6*dot(uv*.8,uv*.8);
  col=1.-exp(-col*1.35); col=pow(col,vec3(.92));
  col+=(hash(gl_FragCoord.xy+t)-.5)/255.;
  gl_FragColor=vec4(col,1.);
}`;
  let gl = null, uRes, uTime, uAlert, uCam;
  try { gl = cg.getContext('webgl', { antialias: false, alpha: false, powerPreference: 'low-power' }); } catch (e) { gl = null; }
  if (gl) {
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) { console.warn(gl.getShaderInfoLog(s)); return null; } return s; };
    const vs = sh(gl.VERTEX_SHADER, 'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}'), fs = sh(gl.FRAGMENT_SHADER, FS);
    if (vs && fs) {
      const pr = gl.createProgram(); gl.attachShader(pr, vs); gl.attachShader(pr, fs); gl.linkProgram(pr);
      if (gl.getProgramParameter(pr, gl.LINK_STATUS)) {
        gl.useProgram(pr);
        const b = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, b); gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
        const loc = gl.getAttribLocation(pr, 'p'); gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
        uRes = gl.getUniformLocation(pr, 'uRes'); uTime = gl.getUniformLocation(pr, 'uTime'); uAlert = gl.getUniformLocation(pr, 'uAlert'); uCam = gl.getUniformLocation(pr, 'uCam');
      } else { console.warn(gl.getProgramInfoLog(pr)); gl = null; }
    } else gl = null;
  }
  if (!gl) { cg.style.display = 'none'; hero.style.background = 'radial-gradient(ellipse at 30% 30%,#0b3a7a 0,transparent 55%),radial-gradient(ellipse at 70% 75%,#0f6a3a 0,transparent 50%),#02040a'; }

  /* ---------- 3D helpers ---------- */
  const cos = Math.cos, sin = Math.sin, PI = Math.PI;
  const Rx = (a) => [1, 0, 0, 0, cos(a), -sin(a), 0, sin(a), cos(a)];
  const Ry = (a) => [cos(a), 0, sin(a), 0, 1, 0, -sin(a), 0, cos(a)];
  const Rz = (a) => [cos(a), -sin(a), 0, sin(a), cos(a), 0, 0, 0, 1];
  const mm = (A, B) => { const o = new Array(9); for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) o[i * 3 + j] = A[i * 3] * B[j] + A[i * 3 + 1] * B[3 + j] + A[i * 3 + 2] * B[6 + j]; return o; };
  const mv = (M, v) => [M[0] * v[0] + M[1] * v[1] + M[2] * v[2], M[3] * v[0] + M[4] * v[1] + M[5] * v[2], M[6] * v[0] + M[7] * v[1] + M[8] * v[2]];
  const clamp = (x, a, b) => Math.max(a, Math.min(b, x));
  const LIGHT = (() => { const l = [-.45, .6, .66], n = Math.hypot(l[0], l[1], l[2]); return [l[0] / n, l[1] / n, l[2] / n]; })();
  const D = 4.4;
  let U = 100, CX = 180, CY = 160;
  const proj = (v) => { const k = D * U / (D - v[2]); return { x: CX + v[0] * k, y: CY - v[1] * k, z: v[2], k: k / D }; };

  /* gold metal that reflects the blue/green nebula; n = surface normal in view space */
  function metal(n, z) {
    const d = n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2];
    const diff = Math.max(0, d) * .7 + .22, spec = Math.pow(Math.max(0, d), 16);
    const rim = Math.pow(1 - Math.abs(n[2]), 2.4), up = Math.max(0, -n[1]);
    let r = 70 + 185 * diff, g = 48 + 150 * diff, b = 12 + 62 * diff;
    r = r * (1 - .42 * rim) + 110 * .42 * rim; g = g * (1 - .42 * rim) + 215 * .42 * rim; b = b * (1 - .42 * rim) + 255 * .42 * rim;
    g += 255 * .15 * up; r += 110 * .08 * up; b += 140 * .08 * up;
    r += 255 * spec * .8; g += 255 * spec * .8; b += 255 * spec * .8;
    const a = alertK * .38; r = r * (1 - a) + 255 * a; g = g * (1 - a) + 70 * a; b = b * (1 - a) + 60 * a;
    const fade = clamp(.62 + .32 * z, .38, 1);
    r = r * fade + 4 * (1 - fade); g = g * fade + 10 * (1 - fade); b = b * fade + 30 * (1 - fade);
    return 'rgb(' + (clamp(r, 0, 255) | 0) + ',' + (clamp(g, 0, 255) | 0) + ',' + (clamp(b, 0, 255) | 0) + ')';
  }

  /* ---------- gyroscope ---------- */
  const items = [];
  function ring(F, rad, tube, ticks) {
    const N = LV >= 2 ? 48 : 84; let prev = null;
    for (let i = 0; i <= N; i++) {
      const th = i / N * 2 * PI, c = cos(th), s = sin(th);
      const P = proj(mv(F, [rad * c, rad * s, 0])), nrm = mv(F, [c, s, 0]);
      if (prev) { const zz = (prev.z + P.z) / 2, ww = tube * P.k * D * 2;
        items.push({ k: 5, z: -9, x1: prev.x, y1: prev.y, x2: P.x, y2: P.y, w: ww + 2.6 });
        items.push({ k: 0, z: zz, x1: prev.x, y1: prev.y, x2: P.x, y2: P.y, w: ww, col: metal(nrm, P.z) }); }
      prev = P;
    }
    if (ticks) for (let j = 0; j < 72; j++) {
      if (LV >= 2 && j % 6) continue;
      const th = j * PI / 36, c = cos(th), s = sin(th), long = j % 6 === 0, r1 = long ? .85 : .9, r2 = 1 - tube * 1.1;
      const A = proj(mv(F, [r1 * c, r1 * s, 0])), B = proj(mv(F, [r2 * c, r2 * s, 0]));
      items.push({ k: 1, z: (A.z + B.z) / 2, x1: A.x, y1: A.y, x2: B.x, y2: B.y, w: long ? 1.7 : 1, col: long ? 'rgba(255,226,150,.9)' : 'rgba(240,200,110,.55)' });
    }
  }
  function rod(F, a, b, w) {
    const A = proj(mv(F, a)), B = proj(mv(F, b)), n = mv(F, [0, 0, 1]);
    const zz = (A.z + B.z) / 2, ww = w * (A.k + B.k) * D;
    items.push({ k: 5, z: -9, x1: A.x, y1: A.y, x2: B.x, y2: B.y, w: ww + 2.6 });
    items.push({ k: 2, z: zz, x1: A.x, y1: A.y, x2: B.x, y2: B.y, w: ww, col: metal(n, zz) });
  }
  function ball(F, p, rad) { const P = proj(mv(F, p)); items.push({ k: 3, z: P.z + .02, x: P.x, y: P.y, r: rad * P.k * D, z0: P.z }); }
  function rotor(F3, a4, rad) {
    const pts = [], N = 44;
    for (let i = 0; i < N; i++) { const th = i / N * 2 * PI + a4; pts.push(proj(mv(F3, [0, rad * cos(th), rad * sin(th)]))); }
    const C = proj(mv(F3, [0, 0, 0])), n = mv(F3, [1, 0, 0]);
    items.push({ k: 4, z: C.z, pts, C, a4, F3, rad, col: metal([Math.abs(n[0]), n[1], n[2]], C.z) });
  }

  function drawItem(it) {
    switch (it.k) {
      case 5:
        fx.lineCap = 'round'; fx.strokeStyle = 'rgba(12,7,2,.8)'; fx.lineWidth = it.w; fx.beginPath(); fx.moveTo(it.x1, it.y1); fx.lineTo(it.x2, it.y2); fx.stroke(); break;
      case 0: case 2:
        fx.lineCap = 'round'; fx.strokeStyle = it.col; fx.lineWidth = it.w; fx.beginPath(); fx.moveTo(it.x1, it.y1); fx.lineTo(it.x2, it.y2); fx.stroke(); break;
      case 1:
        fx.lineCap = 'butt'; fx.strokeStyle = it.col; fx.lineWidth = it.w; fx.beginPath(); fx.moveTo(it.x1, it.y1); fx.lineTo(it.x2, it.y2); fx.stroke(); break;
      case 3: {
        const g = fx.createRadialGradient(it.x - it.r * .35, it.y - it.r * .4, it.r * .1, it.x, it.y, it.r);
        const a = alertK; g.addColorStop(0, '#fff6d0'); g.addColorStop(.35, a > .5 ? '#ff8a7a' : '#e2b650'); g.addColorStop(1, '#3a2508');
        fx.fillStyle = g; fx.beginPath(); fx.arc(it.x, it.y, it.r, 0, 2 * PI); fx.fill(); break;
      }
      case 4: {
        const { pts } = it; fx.beginPath(); fx.moveTo(pts[0].x, pts[0].y); for (let i = 1; i < pts.length; i++) fx.lineTo(pts[i].x, pts[i].y); fx.closePath();
        const g = fx.createRadialGradient(it.C.x, it.C.y, 2, it.C.x, it.C.y, it.rad * U * 1.05);
        g.addColorStop(0, '#7b8ea0'); g.addColorStop(.55, '#26323f'); g.addColorStop(1, '#0c1119'); fx.fillStyle = g; fx.fill();
        // spinning slots
        fx.fillStyle = 'rgba(2,5,10,.88)';
        for (let s = 0; s < 6; s++) {
          const a0 = s * PI / 3 + it.a4 + .12, a1 = a0 + .5, r0 = it.rad * .28, r1 = it.rad * .86, q = [];
          for (const [aa, rr] of [[a0, r0], [a1, r0], [a1, r1], [a0, r1]]) q.push(proj(mv(it.F3, [0, rr * cos(aa), rr * sin(aa)])));
          fx.beginPath(); fx.moveTo(q[0].x, q[0].y); for (let i = 1; i < 4; i++) fx.lineTo(q[i].x, q[i].y); fx.closePath(); fx.fill();
        }
        fx.strokeStyle = it.col; fx.lineWidth = Math.max(2, it.rad * U * .08); fx.lineJoin = 'round';
        fx.beginPath(); fx.moveTo(pts[0].x, pts[0].y); for (let i = 1; i < pts.length; i++) fx.lineTo(pts[i].x, pts[i].y); fx.closePath(); fx.stroke();
        // phosphor edge light
        fx.strokeStyle = alertK > .5 ? 'rgba(255,120,100,.5)' : 'rgba(120,230,255,.45)'; fx.lineWidth = 1;
        fx.beginPath(); fx.moveTo(pts[0].x, pts[0].y); for (let i = 1; i < pts.length; i++) fx.lineTo(pts[i].x, pts[i].y); fx.closePath(); fx.stroke();
      }
    }
  }

  /* ---------- quartz crystals, silk filaments, dust ---------- */
  const CR = []; for (let i = 0; i < 9; i++) CR.push({ a: Math.random() * 2 * PI, sp: (.05 + Math.random() * .07) * (Math.random() < .5 ? -1 : 1), rx: 1.35 + Math.random() * 1.2, ry: .5 + Math.random() * .9, rz: 1.2 + Math.random() * 1.1, ph: Math.random() * 6, s: .1 + Math.random() * .17, w: [Math.random() * .6 + .1, Math.random() * .6 + .1, Math.random() * .5], g: Math.random() < .35 });
  const DUST = []; for (let i = 0; i < 70; i++) DUST.push({ r: 1.15 + Math.random() * .9, a: Math.random() * 2 * PI, sp: (.06 + Math.random() * .16) * (Math.random() < .5 ? -1 : 1), inc: Math.random() * PI, tw: Math.random() * 9, g: Math.random() < .3 });
  const HEX = []; for (let k = 0; k < 6; k++) HEX.push(k * PI / 3);
  function crystal(c, t, V) {
    const M = mm(V, mm(Rx(t * c.w[0] + c.ph), mm(Ry(t * c.w[1]), Rz(t * c.w[2])))), S = c.s * U * 2.2;
    const a = c.a + t * c.sp, pos = [cos(a) * c.rx, sin(a * 1.3 + c.ph) * c.ry, sin(a) * c.rz];
    const verts = [], P = (x, y, z) => { const v = mv(M, [x, y, z]); const w = [pos[0] + v[0] * c.s * 2.2, pos[1] + v[1] * c.s * 2.2, pos[2] + v[2] * c.s * 2.2]; return w; };
    const top = P(0, 1, 0), bot = P(0, -1, 0), tr = HEX.map((h) => P(.38 * cos(h), .55, .38 * sin(h))), br = HEX.map((h) => P(.38 * cos(h), -.55, .38 * sin(h)));
    const faces = [];
    for (let k = 0; k < 6; k++) { const k2 = (k + 1) % 6; faces.push([tr[k], tr[k2], br[k2], br[k]], [top, tr[k2], tr[k]], [bot, br[k], br[k2]]); }
    const col = c.g ? [120, 255, 160] : [110, 215, 255], zc = pos[2];
    const out = faces.map((f) => { const pp = f.map(proj); let n = [0, 0, 0]; { const ax = f[1][0] - f[0][0], ay = f[1][1] - f[0][1], az = f[1][2] - f[0][2], bx = f[2][0] - f[0][0], by = f[2][1] - f[0][1], bz = f[2][2] - f[0][2]; n = [ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx]; const l = Math.hypot(n[0], n[1], n[2]) || 1; n = [n[0] / l, n[1] / l, n[2] / l]; }
      return { pp, n, z: pp.reduce((s, q) => s + q.z, 0) / pp.length }; }).sort((a1, b1) => a1.z - b1.z);
    fx.globalCompositeOperation = 'lighter';
    for (const f of out) {
      const d = Math.abs(f.n[0] * LIGHT[0] + f.n[1] * LIGHT[1] + f.n[2] * LIGHT[2]), sp = Math.pow(d, 14);
      const tw = .5 + .5 * Math.sin(t * 1.3 + c.ph * 3 + f.z * 9), al = .05 + .13 * d + .55 * sp * tw;
      const cc = alertK > .5 ? [255, 110, 100] : col;
      fx.fillStyle = 'rgba(' + cc[0] + ',' + cc[1] + ',' + cc[2] + ',' + al.toFixed(3) + ')';
      fx.beginPath(); fx.moveTo(f.pp[0].x, f.pp[0].y); for (let i = 1; i < f.pp.length; i++) fx.lineTo(f.pp[i].x, f.pp[i].y); fx.closePath(); fx.fill();
      fx.strokeStyle = 'rgba(225,255,255,' + (.16 + .5 * sp * tw + .1 * d).toFixed(3) + ')'; fx.lineWidth = .8; fx.stroke();
    }
    fx.globalCompositeOperation = 'source-over';
    return zc;
  }
  function silk(t) {
    fx.globalCompositeOperation = 'lighter'; fx.lineWidth = .8;
    for (let b = 0; b < 5; b++) for (let s = 0; s < 4; s++) {
      const ph = t * (.12 + b * .02) + b * 1.7, o = s * 2.4, y0 = H * (.18 + b * .16) + Math.sin(ph) * 18;
      fx.strokeStyle = 'rgba(' + (b % 2 ? '170,255,215' : '175,225,255') + ',' + (.05 + .07 * (.5 + .5 * Math.sin(t * 1.4 + s + b))).toFixed(3) + ')';
      fx.beginPath(); fx.moveTo(-10, y0 + o); fx.bezierCurveTo(W * .3, y0 - 50 + Math.sin(ph * 1.3) * 30 + o, W * .6, y0 + 60 + Math.cos(ph) * 30 + o, W + 10, y0 - 10 + o); fx.stroke();
    }
    fx.globalCompositeOperation = 'source-over';
  }

  function drawScene(t) {
    fx.clearRect(0, 0, W, H);
    U = Math.min(W, H) * .29; CX = W / 2; CY = H / 2 + 4;
    const V = mm(Rx(pitch), Ry(yaw));
    // halo behind the gyroscope
    fx.globalCompositeOperation = 'lighter';
    let g = fx.createRadialGradient(CX, CY, U * .2, CX, CY, U * 2.1);
    g.addColorStop(0, alertK > .5 ? 'rgba(255,70,60,.20)' : 'rgba(70,170,255,.20)'); g.addColorStop(.5, alertK > .5 ? 'rgba(255,60,50,.07)' : 'rgba(60,255,160,.06)'); g.addColorStop(1, 'rgba(0,0,0,0)');
    fx.fillStyle = g; fx.fillRect(0, 0, W, H);
    fx.globalCompositeOperation = 'source-over';
    if (LV < 2) silk(t);
    const near = [], nCr = LV >= 3 ? 4 : LV >= 2 ? 6 : CR.length;
    for (let ci = 0; ci < nCr; ci++) { const c = CR[ci]; const zc = Math.sin(c.a + t * c.sp) * c.rz; if (zc < 0) crystal(c, t, V); else near.push(c); }
    // gimbals: outer (spins about Y) -> middle (about its X) -> inner (about its Y) -> rotor (about X)
    const a1 = t * .28, a2 = .75 * sin(t * .37) + .25, a3 = .65 * sin(t * .29 + 1.3), a4 = t * 7.5;
    const F1 = mm(V, Ry(a1)), F2 = mm(F1, Rx(a2)), F3 = mm(F2, Ry(a3));
    items.length = 0;
    ring(F1, 1, .05, true); ring(F2, .78, .042, false); ring(F3, .56, .036, false);
    rod(V, [0, -1.34, 0], [0, -1, 0], .028); rod(V, [0, 1, 0], [0, 1.34, 0], .028); ball(V, [0, -1.34, 0], .05); ball(V, [0, 1.34, 0], .05);
    rod(F1, [-1, 0, 0], [-.78, 0, 0], .03); rod(F1, [.78, 0, 0], [1, 0, 0], .03); ball(F1, [-1, 0, 0], .05); ball(F1, [1, 0, 0], .05);
    rod(F2, [0, -.78, 0], [0, -.56, 0], .028); rod(F2, [0, .56, 0], [0, .78, 0], .028); ball(F2, [0, -.78, 0], .045); ball(F2, [0, .78, 0], .045);
    rod(F3, [-.56, 0, 0], [.56, 0, 0], .034); ball(F3, [-.56, 0, 0], .05); ball(F3, [.56, 0, 0], .05); ball(F3, [0, 0, 0], .07);
    rotor(F3, a4, .4);
    items.sort((p, q) => p.z - q.z);
    for (const it of items) drawItem(it);
    // dust of quartz
    fx.globalCompositeOperation = 'lighter';
    const nD = LV >= 2 ? 30 : DUST.length;
    for (let di = 0; di < nD; di++) {
      const d = DUST[di];
      const a = d.a + t * d.sp, v = mv(V, [d.r * cos(a), d.r * sin(a) * sin(d.inc), d.r * sin(a) * cos(d.inc)]), P = proj(v), tw = .5 + .5 * sin(t * 2 + d.tw);
      fx.fillStyle = alertK > .5 ? 'rgba(255,130,120,' + (.2 + .6 * tw).toFixed(2) + ')' : d.g ? 'rgba(130,255,170,' + (.2 + .6 * tw).toFixed(2) + ')' : 'rgba(190,235,255,' + (.2 + .6 * tw).toFixed(2) + ')';
      fx.fillRect(P.x, P.y, 1.3 + (v[2] > 0 ? .8 : 0), 1.3 + (v[2] > 0 ? .8 : 0));
    }
    fx.globalCompositeOperation = 'source-over';
    for (const c of near) crystal(c, t, V);
    if (alertK > .02) { fx.fillStyle = 'rgba(255,40,30,' + (.07 * alertK * (.5 + .5 * sin(t * 6))).toFixed(3) + ')'; fx.fillRect(0, 0, W, H); }
  }

  /* ---------- loop, size, input ---------- */
  function resize() {
    const r = hero.getBoundingClientRect(); W = Math.max(220, Math.round(r.width)); H = Math.max(200, Math.round(r.height));
    const d2 = LV >= 2 ? 1 : DPR;
    cf.width = Math.round(W * d2); cf.height = Math.round(H * d2); fx.setTransform(d2, 0, 0, d2, 0, 0);
    const gs = GS[LV]; cg.width = Math.round(W * gs); cg.height = Math.round(H * gs); if (gl) gl.viewport(0, 0, cg.width, cg.height);
  }
  let last = performance.now(), tt = 0, gAcc = 0, gCnt = 0, gWarm = 0, gT = 0, gM = 0, flip = 0;
  const gReset = () => { gWarm = 0; gAcc = 0; gCnt = 0; gT = 0; gM = 0; };
  function frame(now) {
    requestAnimationFrame(frame);
    if (!visible || document.hidden) { last = now; gAcc = 0; gCnt = 0; gM = 0; return; }
    if (LV >= 3) { flip ^= 1; if (flip) return; }              // lightest level: draw every other frame (~30 fps)
    const raw = now - last;
    // governor: ignore the warm-up (first 15 frames or 2.5 s: shader compile), then measure real frame time over 40 frames
    // (or 4 s if frames are very slow). If the average is above 38 ms (slower than ~26 fps) go one level lighter.
    // A phone in battery-saver (capped at 30 fps = 33 ms) stays put. Frames after a hidden tab are not counted (last reset above).
    if (!forced && LV < 3) {
      if (!gT) gT = now;
      if (gWarm < 15 && now - gT < 2500) gWarm++;
      else {
        if (!gM) gM = now;
        gAcc += Math.min(raw, 1000); gCnt++;
        if (gCnt >= 40 || (gCnt >= 4 && now - gM > 4000)) {
          const avg = gAcc / gCnt; gAcc = 0; gCnt = 0; gM = 0;
          if (avg > 38) { LV++; gReset(); try { localStorage.setItem('gyroQ', JSON.stringify({ lv: LV, t: Date.now() })); } catch (e) { } resize(); try { console.info('scene quality ->', LV, 'avg ms', avg.toFixed(1)); } catch (e) { } }
        }
      }
    }
    const dt = Math.min(.05, (now - last) / 1000); last = now; tt += dt * (reduce ? .3 : 1);
    alertK += (alertT - alertK) * Math.min(1, dt * 2.5);
    if (!drag) { yaw += vy * dt; pitch = clamp(pitch + vp * dt, -1.2, 1.2); vy *= .94; vp *= .94; yaw += dt * .05; }
    if (gl) { gl.uniform2f(uRes, cg.width, cg.height); gl.uniform1f(uTime, T0 + tt); gl.uniform1f(uAlert, alertK); gl.uniform2f(uCam, yaw * .5, pitch * .5); gl.drawArrays(gl.TRIANGLES, 0, 3); }
    drawScene(T0 + tt);
  }
  hero.addEventListener('pointerdown', (e) => { drag = true; px = e.clientX; py = e.clientY; try { hero.setPointerCapture(e.pointerId); } catch (_) { } });
  hero.addEventListener('pointermove', (e) => { if (!drag) return; const dx = e.clientX - px, dy = e.clientY - py; px = e.clientX; py = e.clientY; yaw += dx * .008; pitch = clamp(pitch + dy * .008, -1.2, 1.2); vy = dx * .5; vp = dy * .5; });
  const up = () => { drag = false; }; hero.addEventListener('pointerup', up); hero.addEventListener('pointercancel', up);
  if ('IntersectionObserver' in window) new IntersectionObserver((es) => { visible = es[0].isIntersecting; }).observe(hero);
  window.addEventListener('resize', resize); resize(); requestAnimationFrame(frame);
  window.Scene = { setAlert(on) { alertT = on ? 1 : 0; }, quality() { return LV; } };
})();
