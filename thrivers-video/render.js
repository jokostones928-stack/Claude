// Frame-accurate renderer: drives index.html's renderAt(t) in headless Chromium,
// pipes JPEG frames into ffmpeg (one segment per worker), then muxes narration + music.
// Usage: node render.js [--fps 30] [--workers 4] [--from 0] [--to <sec>] [--still t1,t2,...] [--out file.mp4]
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const fs = require('fs'), path = require('path');

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => (v.startsWith('--') ? a.concat([[v.slice(2), arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : '1']]) : a), []));
const FPS = +(args.fps || 30), WORKERS = +(args.workers || 4);
const DIR = __dirname, BUILD = path.join(DIR, 'build');

// icons -> build/icons.js
const iconDir = path.join(DIR, 'node_modules/lucide-static/icons');
const icons = {};
for (const f of fs.readdirSync(iconDir)) if (f.endsWith('.svg')) icons[f.slice(0, -4)] = fs.readFileSync(path.join(iconDir, f), 'utf8').replace(/<!--[\s\S]*?-->/g, '').trim();
const html = fs.readFileSync(path.join(DIR, 'index.html'), 'utf8');
const used = {}; for (const m of html.matchAll(/'([a-z0-9-]+)'/g)) if (icons[m[1]]) used[m[1]] = icons[m[1]];
const scenesTxt = fs.readFileSync(path.join(DIR, 'scenes.json'), 'utf8');
for (const m of scenesTxt.matchAll(/"icon": "([a-z0-9-]+)"/g)) if (icons[m[1]]) used[m[1]] = icons[m[1]];
fs.writeFileSync(path.join(BUILD, 'icons.js'), 'window.ICONS=' + JSON.stringify(used) + ';');

const TOTAL = +fs.readFileSync(path.join(BUILD, 'data.js'), 'utf8').match(/TOTAL=([\d.]+)/)[1];
const URL = 'file://' + path.join(DIR, 'index.html');

async function openPage(browser) {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  page.on('pageerror', e => console.error('PAGE ERROR', e.message));
  await page.goto(URL);
  await page.evaluate(() => window.READY);
  return page;
}

async function stills(times) {
  const browser = await chromium.launch();
  const page = await openPage(browser);
  fs.mkdirSync(path.join(BUILD, 'stills'), { recursive: true });
  for (const t of times) {
    await page.evaluate(t => renderAt(t), t);
    await page.screenshot({ path: path.join(BUILD, 'stills', `t${String(t).padStart(6, '0')}.jpg`), type: 'jpeg', quality: 85 });
  }
  await browser.close();
}

async function worker(browser, idx, f0, f1, seg) {
  const page = await openPage(browser);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', String(FPS), seg], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let f = f0; f < f1; f++) {
    await page.evaluate(t => renderAt(t), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 93 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - f0) % 300 === 0) console.log(`[w${idx}] ${f - f0}/${f1 - f0} frames  ${((f - f0) / ((Date.now() - t0) / 1000 + 1e-3)).toFixed(1)} fps`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await page.close();
}

(async () => {
  if (args.still) return stills(args.still.split(',').map(Number));
  const from = +(args.from || 0), to = Math.min(+(args.to || TOTAL), TOTAL);
  const F0 = Math.round(from * FPS), F1 = Math.round(to * FPS);
  const segDir = path.join(BUILD, 'segments'); if (args.mux === undefined) { fs.rmSync(segDir, { recursive: true, force: true }); fs.mkdirSync(segDir, { recursive: true }); }
  if (args.mux === undefined) {
  const browser = await chromium.launch();
  const per = Math.ceil((F1 - F0) / WORKERS), jobs = [], segs = [];
  for (let w = 0; w < WORKERS; w++) {
    const a = F0 + w * per, b = Math.min(F1, a + per); if (a >= b) break;
    const seg = path.join(segDir, `seg${w}.mp4`); segs.push(seg);
    jobs.push(worker(browser, w, a, b, seg));
  }
  await Promise.all(jobs);
  await browser.close();
  fs.writeFileSync(path.join(segDir, 'list.txt'), segs.map(s => `file '${s}'`).join('\n'));
  }
  const out = args.out || path.join(DIR, 'Thrivers_Book_Summary.mp4');
  const dur = (F1 - F0) / FPS;
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(segDir, 'list.txt'),
    '-ss', String(from), '-t', String(dur), '-i', path.join(BUILD, 'narration.wav'),
    '-ss', String(from), '-t', String(dur), '-i', path.join(BUILD, 'music.wav'),
    '-filter_complex', '[1:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[v][vk];[2:a]aresample=48000,aformat=channel_layouts=stereo,volume=0.16[m];[m][vk]sidechaincompress=threshold=0.05:ratio=4:attack=40:release=600[md];[v][md]amix=inputs=2:normalize=0,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[a]',
    '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out], { stdio: 'inherit' });
  console.log('wrote', out);
})();
