"""Build the single-file offline Pack.html bundle for the Hill of Towie project."""

import base64
import json
import os


BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "github project_wind")

MODULE_FILES = {
    "annual_wind_rose_2023_interactive.html": "Wind Rose",
    "wind_uv_anomalies_2023_offline.html": "U/V Component Chart",
    "hill_of_towie_3d_true_scale.html": "3D True Scale",
    "hill_of_towie_interactive_speed.html": "Speed Explorer",
}


def encode_file_b64(path: str) -> str:
    """Return the base64-encoded contents of a file."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def build_home_html() -> str:
    """Create the Home view HTML embedded inside Pack.html."""

    def card(filename: str, title: str, tag: str) -> str:
        return (
            '<div class="card">'
            '  <div>'
            f'    <div class="tag">{tag}</div>'
            f'    <h3>{title}</h3>'
            '  </div>'
            '  <div class="actions">'
            f'    <button onclick="parent.postMessage({{goto:\'{filename}\'}} , \'*\')">Open</button>'
            '  </div>'
            '</div>'
        )

    cards = [card(filename, title, "Project") for filename, title in MODULE_FILES.items()]

    tpl = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Home</title>
<style>
:root{
  --pad:22px;
  --ink:#0f172a;
  --muted:#64748b;
  --line:rgba(148,163,184,.22);
}
*{box-sizing:border-box}
body{
  margin:0;
  font:14px/1.6 system-ui,Segoe UI,Roboto;
  color:var(--ink);
  background:
    radial-gradient(circle at top left, rgba(37,99,235,.10), transparent 34%),
    radial-gradient(circle at top right, rgba(13,148,136,.10), transparent 30%),
    linear-gradient(180deg, #f8fafc 0%, #edf4ff 100%);
}
.hero{text-align:center;padding:36px var(--pad) 10px}
.hero h1{margin:0;font-size:clamp(22px,3.2vw,30px);font-weight:700;letter-spacing:.15px}
.hero .sub{margin-top:8px;color:var(--muted)}
.grid{
  display:grid;
  gap:18px;
  padding:12px var(--pad) 28px;
  grid-template-columns:repeat(auto-fit,minmax(320px,1fr));
  align-content:start;
  min-height:calc(100vh - 56px - 160px)
}
.card{
  border:1px solid var(--line);
  border-radius:22px;
  padding:18px;
  background:rgba(255,255,255,.84);
  backdrop-filter:blur(16px);
  box-shadow:0 18px 44px rgba(15,23,42,.08);
  display:flex;
  flex-direction:column;
  justify-content:space-between;
  min-height:180px;
  transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease
}
.card:hover{
  transform:translateY(-3px);
  border-color:rgba(59,130,246,.28);
  box-shadow:0 22px 54px rgba(15,23,42,.12)
}
.card h3{margin:10px 0 0;font-size:17px}
.tag{
  display:inline-block;
  font-size:12px;
  background:linear-gradient(135deg, rgba(37,99,235,.10), rgba(13,148,136,.12));
  border:1px solid rgba(59,130,246,.18);
  padding:3px 9px;
  border-radius:999px;
  color:#345
}
.actions{margin-top:12px}
.card button{
  border:1px solid rgba(59,130,246,.18);
  background:linear-gradient(180deg, rgba(255,255,255,.96), rgba(239,246,255,.92));
  color:#0f172a;
  border-radius:12px;
  padding:9px 15px;
  cursor:pointer;
  box-shadow:0 10px 24px rgba(37,99,235,.10);
  transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease
}
.card button:hover{
  transform:translateY(-1px);
  background:linear-gradient(180deg, #ffffff, #e0f2fe);
  border-color:rgba(59,130,246,.30);
  box-shadow:0 16px 30px rgba(37,99,235,.15)
}
</style>
</head>
<body>
<section class="hero">
  <h1>Hill of Towie Wind Farm Data Analysis &amp; Visualization</h1>
  <div class="sub">Wenyu Gao</div>
</section>
<section class="grid">__CARDS__</section>
</body>
</html>"""
    return tpl.replace("__CARDS__", "".join(cards))


def main():
    """Validate module pages and assemble the unified Pack.html bundle."""
    missing = [filename for filename in MODULE_FILES if not os.path.exists(os.path.join(BASE_DIR, filename))]
    if missing:
        raise FileNotFoundError("Missing files:\\n- " + "\\n- ".join(missing))

    pages_boot = {
        "__home__": base64.b64encode(build_home_html().encode("utf-8")).decode("ascii")
    }
    pages_rest = {filename: encode_file_b64(os.path.join(BASE_DIR, filename)) for filename in MODULE_FILES}

    nav_buttons = "\n".join(
        f'<button class="tab" data-file="{filename}">{title}</button>'
        for filename, title in MODULE_FILES.items()
    )

    template = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hill of Towie - All-in-One</title>
<style>
:root{
  --h:64px;
  --ink:#0f172a;
  --muted:#64748b;
  --line:rgba(148,163,184,.22);
}
*{box-sizing:border-box}
body{
  margin:0;
  background:
    radial-gradient(circle at top left, rgba(37,99,235,.10), transparent 28%),
    radial-gradient(circle at top right, rgba(13,148,136,.08), transparent 24%),
    linear-gradient(180deg, #f8fafc 0%, #edf4ff 100%);
  color:var(--ink);
  font:14px/1.5 system-ui,Segoe UI,Roboto;
}
header.nav{
  height:var(--h);
  display:flex;
  align-items:center;
  gap:12px;
  padding:0 18px;
  border-bottom:1px solid var(--line);
  position:sticky;
  top:0;
  background:rgba(255,255,255,.72);
  backdrop-filter:blur(18px);
  box-shadow:0 10px 30px rgba(15,23,42,.06);
  z-index:10
}
.brand{font-weight:700;letter-spacing:.2px;color:#0f172a}
.links{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.sp{flex:1}
.tab{
  border:1px solid rgba(59,130,246,.16);
  background:linear-gradient(180deg, rgba(255,255,255,.95), rgba(241,245,249,.92));
  color:var(--ink);
  border-radius:12px;
  padding:7px 13px;
  cursor:pointer;
  box-shadow:0 10px 24px rgba(37,99,235,.08);
  transition:transform .18s ease, box-shadow .18s ease, border-color .18s ease, background .18s ease
}
.tab:hover{
  transform:translateY(-1px);
  background:linear-gradient(180deg, #ffffff, #eef6ff);
  border-color:rgba(59,130,246,.26);
  box-shadow:0 14px 30px rgba(37,99,235,.12)
}
.tab.active{
  background:linear-gradient(135deg, rgba(37,99,235,.14), rgba(13,148,136,.14));
  border-color:rgba(59,130,246,.30)
}
#viewerWrap{
  position:fixed;
  inset:var(--h) 0 0 0;
  background:linear-gradient(180deg, rgba(255,255,255,.38), rgba(255,255,255,.06))
}
iframe{width:100%;height:100%;border:0;background:#fff}
#loading{
  position:absolute;
  top:18px;
  right:20px;
  display:none;
  align-items:center;
  gap:10px;
  padding:10px 14px;
  background:rgba(255,255,255,.88);
  border:1px solid var(--line);
  border-radius:999px;
  box-shadow:0 18px 36px rgba(15,23,42,.10);
  color:var(--ink);
  font-weight:600;
  z-index:15
}
.loadingDot{
  width:10px;
  height:10px;
  border-radius:999px;
  background:linear-gradient(135deg, #2563eb, #0d9488);
  box-shadow:0 0 0 6px rgba(37,99,235,.12);
  animation:pulse 1.2s ease-in-out infinite
}
#progressOverlay{
  position:absolute;
  inset:0;
  display:grid;
  place-items:center;
  background:
    radial-gradient(circle at top left, rgba(37,99,235,.08), transparent 28%),
    radial-gradient(circle at top right, rgba(13,148,136,.08), transparent 24%),
    linear-gradient(180deg, rgba(248,250,252,.96), rgba(237,244,255,.92));
  z-index:20;
  transition:opacity .24s ease, visibility .24s ease
}
.progress{
  width:min(470px,86vw);
  background:rgba(255,255,255,.84);
  border:1px solid var(--line);
  border-radius:22px;
  box-shadow:0 30px 70px rgba(15,23,42,.14);
  padding:24px 22px 18px;
  backdrop-filter:blur(18px)
}
.progress .eyebrow{
  font-size:12px;
  letter-spacing:.12em;
  text-transform:uppercase;
  color:#0d9488;
  text-align:center
}
.progress .title{
  margin-top:10px;
  font-weight:700;
  font-size:22px;
  text-align:center
}
.progress .hint{
  margin-top:6px;
  text-align:center;
  color:var(--muted)
}
.bar{
  height:12px;
  background:rgba(226,232,240,.72);
  border-radius:999px;
  overflow:hidden;
  margin-top:16px;
  border:1px solid rgba(226,232,240,.96)
}
.fill{
  height:100%;
  width:0%;
  background:linear-gradient(90deg, #2563eb, #0d9488);
  border-radius:999px;
  box-shadow:0 10px 24px rgba(37,99,235,.28);
  position:relative;
  transition:width .18s linear
}
.fill::after{
  content:"";
  position:absolute;
  inset:0;
  background:linear-gradient(90deg, transparent, rgba(255,255,255,.52), transparent);
  animation:shimmer 1.2s linear infinite
}
.progressMeta{
  display:flex;
  align-items:center;
  justify-content:space-between;
  margin-top:10px;
  gap:12px
}
.pct{font-weight:700}
.meterLabel{color:var(--muted);font-size:13px}
@keyframes shimmer{
  from{transform:translateX(-100%)}
  to{transform:translateX(100%)}
}
@keyframes pulse{
  0%,100%{transform:scale(1);opacity:1}
  50%{transform:scale(.82);opacity:.72}
}
</style>
</head>
<body>
<header class="nav">
  <div class="brand">Hill of Towie</div>
  <div class="links">
    <button class="tab" data-file="__home__">Home</button>
    __NAV_BUTTONS__
  </div>
  <div class="sp"></div>
  <button class="tab" id="openNew" title="Open current view in new tab">Open</button>
  <button class="tab" id="reload" title="Reload current view">Reload</button>
  <button class="tab" id="fullscreen" title="Fullscreen">Fullscreen</button>
</header>

<div id="viewerWrap">
  <div id="progressOverlay">
    <div class="progress">
      <div class="eyebrow">Preparing Pack</div>
      <div class="title" id="progressTitle">Loading Dashboard</div>
      <div class="hint" id="progressHint">Building the first view...</div>
      <div class="bar"><div class="fill" id="fill" style="width:24%"></div></div>
      <div class="progressMeta">
        <div class="pct" id="pct">24%</div>
        <div class="meterLabel" id="meterLabel">Bootstrapping</div>
      </div>
    </div>
  </div>

  <div id="loading"><span class="loadingDot"></span><span id="loadingLabel">Loading view...</span></div>
  <iframe id="viewer" sandbox="allow-scripts allow-downloads allow-forms"></iframe>
</div>

<script>
const PAGES_BOOT = __PAGES_BOOT__;
const PAGE_LABELS = __PAGE_LABELS__;
</script>

<script id="pages-json" type="application/json">__PAGES_REST__</script>

<script>
function b64ToBytes(b64){
  const bin = atob(b64), len = bin.length, arr = new Uint8Array(len);
  for(let i = 0; i < len; i++) arr[i] = bin.charCodeAt(i);
  return arr;
}
function b64ToUtf8(b64){
  return new TextDecoder('utf-8').decode(b64ToBytes(b64));
}

const progWrap = document.getElementById('progressOverlay');
const fill = document.getElementById('fill');
const pct = document.getElementById('pct');
const progTitle = document.getElementById('progressTitle');
const progHint = document.getElementById('progressHint');
const meterLabel = document.getElementById('meterLabel');
const viewer = document.getElementById('viewer');
const loading = document.getElementById('loading');
const loadingLabel = document.getElementById('loadingLabel');

let progressValue = 24;
let progressRaf = null;
let initialDone = false;
let restParsed = false;
let restParsing = false;
let PAGES = Object.assign({}, PAGES_BOOT);

function renderProgress(value){
  fill.style.width = value + '%';
  pct.textContent = Math.round(value) + '%';
}

function animateProgress(target){
  const from = progressValue;
  const to = Math.max(from, Math.min(target, 100));
  if(progressRaf) cancelAnimationFrame(progressRaf);
  const start = performance.now();
  const dur = Math.max(180, (to - from) * 10);
  function frame(ts){
    const t = Math.min(1, (ts - start) / dur);
    progressValue = from + (to - from) * t;
    renderProgress(progressValue);
    if(t < 1) progressRaf = requestAnimationFrame(frame);
  }
  progressRaf = requestAnimationFrame(frame);
}

function displayName(name){
  return PAGE_LABELS[name] || 'Home';
}

function setProgress(target, title, hint, meta){
  if(title) progTitle.textContent = title;
  if(hint) progHint.textContent = hint;
  if(meta) meterLabel.textContent = meta;
  animateProgress(target);
}

function finishProgress(name){
  setProgress(100, 'Ready', displayName(name) + ' is ready.', 'Complete');
  setTimeout(() => {
    progWrap.style.opacity = '0';
    progWrap.style.visibility = 'hidden';
    initialDone = true;
  }, 240);
}

function showLoading(name){
  loadingLabel.textContent = 'Loading ' + displayName(name) + '...';
  loading.style.display = 'flex';
}

function hideLoading(){
  loading.style.display = 'none';
}

function fitPlotly(doc, current){
  if(!doc) return;
  const w = doc.defaultView;
  let style = doc.getElementById('codex-fitplotly-style');
  if(!style){
    style = doc.createElement('style');
    style.id = 'codex-fitplotly-style';
    (doc.head || doc.documentElement).appendChild(style);
  }

  function getDims(){
    const rect = viewer.getBoundingClientRect ? viewer.getBoundingClientRect() : null;
    const rawW = Math.floor(rect && rect.width ? rect.width : (w ? w.innerWidth : (doc.documentElement.clientWidth || 1200)));
    const rawH = Math.floor(rect && rect.height ? rect.height : (w ? w.innerHeight : (doc.documentElement.clientHeight || 800)));
    return {
      targetW: Math.max(480, rawW || 1200),
      targetH: Math.max(620, (rawH || 800) - 4)
    };
  }

  function resizeAll(){
    const {targetW, targetH} = getDims();
    style.textContent = `
      html,body{height:100%;width:100%;overflow-x:hidden;}
      body{margin:0;padding:0;}
      .plotly-graph-div,.js-plotly-plot{max-width:100% !important;}
    `;

    try{
      const root = doc.body && doc.body.firstElementChild;
      if(root){
        root.style.width = '100%';
        root.style.margin = '0';
        if(
          current === 'annual_wind_rose_2023_interactive.html' ||
          current === 'hill_of_towie_3d_true_scale.html'
        ){
          root.style.height = targetH + 'px';
          root.style.minHeight = targetH + 'px';
        }
      }

      if(current === 'annual_wind_rose_2023_interactive.html' && w && w.Plotly){
        const wrap = doc.getElementById('wr-wrap');
        const panel = doc.getElementById('wr-controls');
        const fig = doc.getElementById('windrose');
        if(wrap && fig){
          const panelW = panel ? Math.ceil(panel.getBoundingClientRect().width || 220) : 220;
          const figW = Math.max(460, targetW - panelW - 40);
          wrap.style.display = 'flex';
          wrap.style.alignItems = 'stretch';
          wrap.style.gap = '16px';
          wrap.style.padding = '8px 8px 8px 0';
          wrap.style.height = targetH + 'px';
          wrap.style.minHeight = targetH + 'px';
          fig.style.flex = '1 1 auto';
          fig.style.minWidth = '0';
          fig.style.height = targetH + 'px';
          fig.style.minHeight = targetH + 'px';
          fig.style.width = figW + 'px';
          if(panel){
            panel.style.flex = '0 0 auto';
            panel.style.maxHeight = (targetH - 16) + 'px';
            panel.style.overflowY = 'auto';
          }
          w.Plotly.relayout(fig, {
            autosize: true,
            height: targetH,
            width: figW,
            'margin.l': 20,
            'margin.r': 12,
            'margin.t': 36,
            'margin.b': 20,
            'polar.domain.x': [0.04, 0.96],
            'polar.domain.y': [0.05, 0.95]
          });
          w.Plotly.Plots.resize(fig);
          return;
        }
      }

      if(w && w.Plotly){
        doc.querySelectorAll('.plotly-graph-div').forEach(el => {
          try{
            el.style.height = targetH + 'px';
            el.style.width = targetW + 'px';
            const relayout = {
              autosize: true,
              height: targetH,
              width: targetW,
              'margin.l': 20,
              'margin.r': 20,
              'margin.t': 30,
              'margin.b': 20
            };
            if(current === 'hill_of_towie_3d_true_scale.html'){
              relayout['margin.l'] = 0;
              relayout['margin.r'] = 0;
              relayout['margin.t'] = 36;
              relayout['margin.b'] = 0;
              relayout['scene.aspectmode'] = 'data';
              relayout['scene.domain.x'] = [0, 1];
              relayout['scene.domain.y'] = [0, 1];
            }else if(current === 'hill_of_towie_interactive_speed.html'){
              relayout['scene.aspectmode'] = 'data';
            }
            w.Plotly.relayout(el, relayout);
            w.Plotly.Plots.resize(el);
          }catch(e){}
        });
      }
    }catch(e){}
  }

  resizeAll();
  setTimeout(resizeAll, 150);
  setTimeout(resizeAll, 350);
  setTimeout(resizeAll, 700);

  try{
    const ob = new MutationObserver(() => setTimeout(resizeAll, 60));
    ob.observe(doc.body || doc.documentElement, {childList:true, subtree:true});
    if(w) w.addEventListener('resize', () => setTimeout(resizeAll, 60));
  }catch(e){}
}

function setActive(name){
  document.querySelectorAll('.tab[data-file]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.file === name);
  });
}

function parseRestPages(){
  if(restParsed || restParsing) return;
  restParsing = true;
  setProgress(58, 'Unpacking Modules', 'Decoding the embedded module pages.', 'Parsing bundle');
  setTimeout(() => {
    try{
      const txt = document.getElementById('pages-json').textContent;
      const rest = JSON.parse(txt);
      Object.assign(PAGES, rest);
      restParsed = true;
      setProgress(80, 'Modules Ready', 'Embedded pages decoded successfully.', 'Bundle ready');
    }catch(err){
      console.error(err);
    }finally{
      restParsing = false;
    }
  }, 0);
}

function waitForPage(name, cb, tries = 80){
  if(PAGES[name]) return cb();
  if(tries <= 0) return;
  setTimeout(() => waitForPage(name, cb, tries - 1), 120);
}

function getCurrentView(){
  const match = (new URL(location.href)).hash.match(/view=([^&]+)/);
  return match ? decodeURIComponent(match[1]) : "__home__";
}

function load(name){
  if(!PAGES[name] && name !== "__home__") parseRestPages();
  if(!PAGES[name] && name === "__home__") name = "__home__";

  showLoading(name);
  setActive(name);

  const url = new URL(location.href);
  url.hash = 'view=' + encodeURIComponent(name);
  history.replaceState(null, '', url);
  localStorage.setItem('lastView', name);

  const exec = () => {
    if(!initialDone){
      setProgress(
        name === "__home__" ? 34 : 86,
        name === "__home__" ? 'Rendering Home' : 'Opening Module',
        name === "__home__" ? 'Drawing overview cards and controls.' : 'Rendering ' + displayName(name) + '.',
        'Building view'
      );
    }
    viewer.srcdoc = b64ToUtf8(PAGES[name]);
  };

  if(PAGES[name]) exec();
  else waitForPage(name, exec);
}

viewer.addEventListener('load', () => {
  hideLoading();
  const current = getCurrentView();
  if(!initialDone) finishProgress(current);
  try{
    if(
      current === 'annual_wind_rose_2023_interactive.html' ||
      current === 'hill_of_towie_3d_true_scale.html' ||
      current === 'hill_of_towie_interactive_speed.html'
    ){
      fitPlotly(viewer.contentDocument, current);
    }
  }catch(e){}
});

document.querySelectorAll('.tab[data-file]').forEach(btn => {
  btn.addEventListener('click', () => load(btn.dataset.file));
});

window.addEventListener('message', (e) => {
  try{
    const data = e && e.data;
    if(data && typeof data === 'object' && data.goto) load(data.goto);
  }catch(err){}
});

document.getElementById('openNew').onclick = function(){
  const current = getCurrentView();
  const bytes = b64ToBytes(PAGES[current] || PAGES.__home__);
  const blob = new Blob([bytes], {type:'text/html;charset=utf-8'});
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank');
};

document.getElementById('reload').onclick = function(){
  load(getCurrentView());
};

document.getElementById('fullscreen').onclick = function(){
  viewer.requestFullscreen?.();
};

setProgress(28, 'Loading Dashboard', 'Preparing navigation and the first view.', 'Bootstrapping');
const fromHash = (new URL(location.href)).hash.match(/view=([^&]+)/);
const init = fromHash
  ? decodeURIComponent(fromHash[1])
  : (localStorage.getItem('lastView') || "__home__");
load(init);
setTimeout(parseRestPages, 30);
</script>

</body>
</html>"""

    html = (
        template
        .replace("__NAV_BUTTONS__", nav_buttons)
        .replace("__PAGES_BOOT__", json.dumps(pages_boot, ensure_ascii=True))
        .replace("__PAGES_REST__", json.dumps(pages_rest, ensure_ascii=True))
        .replace("__PAGE_LABELS__", json.dumps({"__home__": "Home", **MODULE_FILES}, ensure_ascii=True))
    )

    out_path = os.path.join(BASE_DIR, "Pack.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)

    print("[OK] Wrote:", out_path, f"~{len(html) / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
