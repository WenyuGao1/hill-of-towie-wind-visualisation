"""Generate the terrain-aware Speed Explorer module for the unified pack."""

import json
import math
import os
import re
import tempfile
import warnings
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import rasterio
import trimesh
from pyproj import Transformer
from rasterio.merge import merge
from rasterio.windows import from_bounds
from scipy.interpolate import RegularGridInterpolator
from tqdm import tqdm

from common_paths import (
    DEM_ROOT,
    META_CSV,
    MODEL_MEMBER,
    MODEL_ZIP,
    OUTPUT_DIR,
    WIND_ROSE_CLEAN_DIR,
)

warnings.filterwarnings("ignore")

# ========= Paths =========
SCADA_DIR = str(WIND_ROSE_CLEAN_DIR)
OUT_HTML = OUTPUT_DIR / "hill_of_towie_interactive_speed.html"
DIV_ID = "speed_explorer_plot"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def extract_turbine_dae() -> str:
    """Extract the turbine DAE model into a reusable temporary directory."""
    temp_dir = Path(tempfile.gettempdir()) / "hill_of_towie_model"
    temp_dir.mkdir(parents=True, exist_ok=True)
    model_path = temp_dir / Path(MODEL_MEMBER).name
    if not model_path.exists():
        with zipfile.ZipFile(MODEL_ZIP) as archive:
            archive.extract(MODEL_MEMBER, temp_dir)
        extracted = temp_dir / MODEL_MEMBER
        extracted.replace(model_path)
        extracted_parent = temp_dir / Path(MODEL_MEMBER).parts[0]
        if extracted_parent.exists() and extracted_parent.is_dir():
            try:
                extracted_parent.rmdir()
            except OSError:
                pass
    return str(model_path)

# ========= CONFIG =========
# 3D visualization parameters
ROTOR_D         = 93.0
CT_9MS          = 0.86
WAKE_K          = 0.05
MAX_WAKELEN_D   = 35.0
REC_P_FIXED     = 0.70
TERRAIN_ON      = True
BETA_TERRAIN    = 0.15
FETCH_FACTOR    = 15.0
S_CLIP          = (-0.20, 0.20)
PATH_AWARE      = False
SCENE_DOMAIN_X  = [0.00, 0.72]
BAR_DOMAIN_X    = [0.75, 1.00]
BAR_X_MAX       = 25.0
BAR_SHOW_LABEL  = True

# Interaction and binning parameters
INIT_DIR_DEG    = 180          # Default wind direction
DIR_STEP_DEG    = 5            # Direction step used for bin centers
SPEEDS_T15      = list(range(3, 26))  # T15 speed slider values (integer m/s)
INIT_T15        = 9            # Default T15 wind speed
SPD_BIN_HALF    = 0.5          # Half-width of the speed bin (+/-0.5 m/s)
MIN_SAMPLES     = 5

# ============= 1) Load turbine metadata and StationId mapping =============
meta_raw = pd.read_csv(META_CSV)
def find_column(cands, df):
    """Return the first matching column name from a list of candidates."""
    for c in cands:
        if c in df.columns: return c
    lower = {c.lower(): c for c in df.columns}
    for c in cands:
        if c.lower() in lower: return lower[c.lower()]
    return None

tid_col = find_column(['Turbine Name','tid','Turbine','Name'], meta_raw)
lat_col = find_column(['Latitude','lat'], meta_raw)
lon_col = find_column(['Longitude','lon'], meta_raw)
hh_col  = find_column(['Hub Height (m)','hub_h','HubHeight'], meta_raw)
sid_col = None
for c in meta_raw.columns:
    if re.search(r'station.*id', c, re.I):
        sid_col = c; break
if not all([tid_col, lat_col, lon_col, hh_col]):
    raise SystemExit("META_CSV is missing one or more required columns: Turbine Name, Latitude, Longitude, Hub Height (m).")
if not sid_col:
    raise SystemExit("META_CSV does not contain a StationId column.")

dfm = meta_raw.rename(columns={
    tid_col:'tid', lat_col:'lat', lon_col:'lon', hh_col:'hub_h', sid_col:'sid'
})
def _tid_num(t):
    s = str(t); dig = ''.join(ch for ch in s if s and str.isdigit(ch))
    return int(dig) if dig else 0
dfm['tid'] = dfm['tid'].astype(str).str.strip()
dfm = dfm.sort_values(by='tid', key=lambda s: s.map(_tid_num)).reset_index(drop=True)
TID_ORDERED = dfm['tid'].tolist()
sid2tid = dict(zip(dfm['sid'].astype(int), dfm['tid']))

# Convert longitude/latitude to British National Grid coordinates
trans = Transformer.from_crs(4326, 27700, always_xy=True)
dfm['x'], dfm['y'] = trans.transform(dfm.lon.values, dfm.lat.values)
X, Y, HUB_H = dfm.x.values, dfm.y.values, dfm.hub_h.values
N_TURB = len(dfm)

# ============= 2) Read SCADA data and build a timestamp x turbine table =============
def choose_ws_col(df):
    """Return the first supported wind-speed column from a SCADA file."""
    for c in ["wtc_AcWindSp_mean","wtc_PrWindSp_mean","wtc_SeWindSp_mean",
              "wtc_SecAnemo_mean","wtc_PriAnemo_mean"]:
        if c in df.columns: return c
    raise SystemExit("No supported wind-speed column was found in the SCADA files.")

def parse_timestamp(s):
    """Parse timestamps while coercing malformed rows to NaT."""
    return pd.to_datetime(s, errors='coerce')

# Match the cleaned 2023 SCADA files.
files = sorted([os.path.join(SCADA_DIR,f) for f in os.listdir(SCADA_DIR)
                if re.match(r"tblSCTurbine_2023_\d{2}_cleaned\.csv$", f)])
if not files:
    raise SystemExit("No cleaned 2023 SCADA files were found in the expected directory.")

rows = []
for fp in tqdm(files, desc="Read SCADA"):
    df = pd.read_csv(fp, sep=None, engine='python')
    time_col = "wtc_CurTime_endvalue" if "wtc_CurTime_endvalue" in df.columns else \
               ("TimeStamp" if "TimeStamp" in df.columns else None)
    if time_col is None or "StationId" not in df.columns:
        continue
    ws_col = choose_ws_col(df)
    dir_col = "wtc_ActualWindDirection_mean"
    if dir_col not in df.columns:
        raise SystemExit("The SCADA files do not contain wtc_ActualWindDirection_mean.")

    tmp = pd.DataFrame({
        "time": parse_timestamp(df[time_col]),
        "sid": pd.to_numeric(df["StationId"], errors='coerce').astype("Int64"),
        "ws":  pd.to_numeric(df[ws_col], errors='coerce'),
        "wd":  pd.to_numeric(df[dir_col], errors='coerce')
    }).dropna(subset=['time','sid'])
    tmp['tid'] = tmp['sid'].astype(int).map(sid2tid)
    tmp = tmp.dropna(subset=['tid'])
    rows.append(tmp[['time','tid','ws','wd']])

scada = pd.concat(rows, ignore_index=True).sort_values('time')
scada.loc[(scada['wd']<0)|(scada['wd']>360),'wd'] = np.nan

# Wide wind-speed table: timestamp x turbine
pivot_ws = scada.pivot_table(index='time', columns='tid', values='ws', aggfunc='mean')
# T15 wind direction and wind-speed series
t15_df = scada[scada['tid']=='T15'][['time','ws','wd']].dropna()
t15_df = t15_df.drop_duplicates(subset=['time']).set_index('time').sort_index()
t15_wd = t15_df['wd']
t15_ws = t15_df['ws']

# ============= 3) Precompute mean turbine speeds and sample counts by (dir, U_T15) =============
DIRS = list(range(0, 360, DIR_STEP_DEG))
def circular_difference(a, b):
    """Return the signed shortest angular difference in degrees."""
    return (a - b + 180) % 360 - 180

def mean_speeds_for(times_sel):
    """Compute mean turbine wind speeds for the selected timestamps."""
    if len(times_sel)==0:
        return [0.0]*len(TID_ORDERED)
    ws_block = pivot_ws.reindex(times_sel).astype(float)
    means = ws_block[TID_ORDERED].mean(axis=0, skipna=True).values
    means = np.nan_to_num(means, nan=0.0).tolist()
    return means

GRID = {}     # GRID[dir][spd] = [u1, u2, ...] ordered by TID_ORDERED
COUNTS = {}   # COUNTS[dir][spd] = N

half = DIR_STEP_DEG/2.0
for d in tqdm(DIRS, desc="Aggregate by (dir, U15)"):
    dir_mask = np.abs(circular_difference(t15_wd.values, d)) <= half
    times_dir = t15_wd.index.values[dir_mask]
    GRID[d] = {}
    COUNTS[d] = {}
    for u in SPEEDS_T15:
        spd_mask = np.abs(t15_ws.loc[times_dir] - u) <= SPD_BIN_HALF
        times_sel = t15_ws.loc[times_dir].index.values[spd_mask.values]
        times_sel = pd.DatetimeIndex(times_sel)
        COUNTS[d][u] = int(len(times_sel))
        GRID[d][u] = mean_speeds_for(times_sel)

# ============= 4) Crop the DEM and prepare 3D terrain surfaces =============
buf = 1000
xmin, xmax = X.min()-buf, X.max()+buf
ymin, ymax = Y.min()-buf, Y.max()+buf
bbox_target = rasterio.coords.BoundingBox(xmin,ymin,xmax,ymax)

def overlap(b1, b2):
    """Return True when two bounding boxes overlap."""
    return not (b1.right<b2.left or b1.left>b2.right or b1.top<b2.bottom or b1.bottom>b2.top)

asc = [os.path.join(r,f) for r,_,fs in os.walk(DEM_ROOT) for f in fs if f.lower().endswith('.asc')]
tiles = [f for f in asc if overlap(rasterio.open(f).bounds, bbox_target)]
if not tiles:
    raise SystemExit("No DEM tiles overlap the requested terrain window.")

full, tf_full = merge([rasterio.open(f) for f in tiles])
win = from_bounds(xmin, ymin, xmax, ymax, tf_full)
ro, co, ht, wd = map(int,(win.row_off, win.col_off, win.height, win.width))
dem = full[:, ro:ro+ht, co:co+wd]
tf = rasterio.windows.transform(win, tf_full)
ys = np.arange(ht)*tf[4] + tf.f
xs = np.arange(wd)*tf[0] + tf.c

dem_flip = dem[0, ::-1, :]
ys_inc   = ys[::-1]
get_z  = RegularGridInterpolator((ys_inc, xs), dem_flip, bounds_error=False, fill_value=None)

dy = abs(tf[4]); dx = tf[0]
gy_flip, gx_flip = np.gradient(dem_flip, dy, dx)
get_gx = RegularGridInterpolator((ys_inc, xs), gx_flip, bounds_error=False, fill_value=0.0)
get_gy = RegularGridInterpolator((ys_inc, xs), gy_flip, bounds_error=False, fill_value=0.0)

GND_Z = get_z((Y, X))
HUB_Z = GND_Z + dfm['hub_h'].values

max_dim = max(dem_flip.shape)
step_ds = max(1, int(np.ceil(max_dim/300)))
dem_ds = dem_flip[::step_ds, ::step_ds].astype(np.float32)
xs_ds = xs[::step_ds]; ys_ds = ys_inc[::step_ds]
Xg_ds, Yg_ds = np.meshgrid(xs_ds, ys_ds)

# Turbine 3D
m0 = trimesh.load(extract_turbine_dae())
m0 = m0.to_geometry() if hasattr(m0,"to_geometry") else m0.dump(concatenate=True)
m0.apply_scale(np.mean(dfm['hub_h']) / (m0.bounds[1][2]-m0.bounds[0][2]))
v0, f0 = m0.vertices, m0.faces
meshes = [trimesh.Trimesh(v0+np.array([x,y,z-m0.centroid[2]]), f0, process=False)
          for x,y,z in zip(X,Y,HUB_Z)]
all_mesh = trimesh.util.concatenate(meshes)

# 3D helper geometry
R = ROTOR_D/2.0; k = WAKE_K
def wake_len_for_recovery(p, CT, k, D):
    """Estimate wake length from a fixed recovery threshold."""
    p = float(np.clip(p, 0.01, 0.99))
    num = (1.0 - math.sqrt(max(1.0-CT, 0.0)))
    denom = max(1.0 - p, 1e-6)
    root = math.sqrt(num/denom)
    x = (D/(2.0*k)) * (root - 1.0)
    return max(0.5*D, min(x, MAX_WAKELEN_D*D))

nz, nt = 12, 24
s_axis = np.linspace(0.0, 1.0, nz)
th = np.linspace(0, 2*np.pi, nt)
ss, tt = np.meshgrid(s_axis, th)
ss = ss.ravel().astype(np.float32); tt = tt.ravel().astype(np.float32)

faces = []
for i in range(nt-1):
    for j in range(nz-1):
        a=j+i*nz; b=j+1+i*nz; c=j+1+(i+1)*nz; d=j+(i+1)*nz
        faces += [[a,b,c],[a,c,d]]
faces = np.asarray(faces, dtype=np.int32)
faces_i, faces_j, faces_k = faces[:,0], faces[:,1], faces[:,2]

def build_wake_xyz(dir_deg: float, x_len_m: float):
    """Build wake cone coordinates for a single wind direction."""
    ang = math.radians(-dir_deg + 90 + 180)
    Rz = np.array([[math.cos(ang),-math.sin(ang),0],
                   [math.sin(ang), math.cos(ang),0],
                   [0,0,1]], dtype=np.float32)
    zz = (ss * x_len_m).astype(np.float32)
    rr = (ROTOR_D/2.0 + k*zz).astype(np.float32)
    cone_unit = np.column_stack([zz, (rr*np.cos(tt)), (rr*np.sin(tt))]).astype(np.float32)

    cones_xyz, touches_xyz = [], []
    for x0, y0, z0 in zip(X.astype(np.float32), Y.astype(np.float32), HUB_Z.astype(np.float32)):
        vtx = cone_unit @ Rz.T
        vtx[:,0] = vtx[:,0] + x0
        vtx[:,1] = vtx[:,1] + y0
        vtx[:,2] = vtx[:,2] + z0
        z_ground = get_z((vtx[:,1], vtx[:,0])).astype(np.float32)
        z_adj = np.maximum(vtx[:,2], z_ground + 2).astype(np.float32)
        cones_xyz.append((vtx[:,0], vtx[:,1], z_adj))
        touched_idx = np.where(vtx[:,2] < z_ground)[0]
        if len(touched_idx) > 0:
            touches_xyz.append((vtx[touched_idx,0].astype(np.float32),
                                vtx[touched_idx,1].astype(np.float32),
                                z_ground[touched_idx].astype(np.float32)))
        else:
            touches_xyz.append((np.array([],dtype=np.float32),
                                np.array([],dtype=np.float32),
                                np.array([],dtype=np.float32)))
    return cones_xyz, touches_xyz
# Initial 3D layers
terrain = go.Surface(z=dem_ds, x=Xg_ds, y=Yg_ds, colorscale='Greens', opacity=1.0, showscale=False)
turbines = go.Mesh3d(
    x=all_mesh.vertices[:,0], y=all_mesh.vertices[:,1], z=all_mesh.vertices[:,2],
    i=all_mesh.faces[:,0], j=all_mesh.faces[:,1], k=all_mesh.faces[:,2],
    color='lightgray', opacity=1.0, name='Turbines'
)
labels = go.Scatter3d(x=X, y=Y, z=HUB_Z + 10, mode='text',
                      text=[str(tid) for tid in TID_ORDERED],
                      textfont=dict(color='black', size=13),
                      showlegend=False, name='Turbine ID')

X_LEN_FIXED = wake_len_for_recovery(REC_P_FIXED, CT_9MS, WAKE_K, ROTOR_D)
cones0, touches0 = build_wake_xyz(INIT_DIR_DEG, X_LEN_FIXED)

# Right-side bar chart seeded from the initial GRID slice
def make_speed_bar_from_grid(GRID, d, u):
    """Build the turbine speed bar chart for a given direction and T15 speed."""
    xs = GRID[d][u]
    texts = [f"{v:.2f} m/s" for v in xs]
    return go.Bar(
        x=xs, y=TID_ORDERED, orientation='h', xaxis='x2', yaxis='y2',
        marker=dict(color=xs, colorscale='Bluered', cmin=0, cmax=BAR_X_MAX, showscale=False),
        text=texts if BAR_SHOW_LABEL else None,
        textposition='outside' if BAR_SHOW_LABEL else None,
        hovertemplate="Turbine %{y}<br>U=%{x:.2f} m/s<extra></extra>",
        name="Wind speed", showlegend=False
    )

bar0 = make_speed_bar_from_grid(GRID, INIT_DIR_DEG, INIT_T15)

fig = go.Figure(data=[terrain, turbines, labels])
for i in range(N_TURB):
    x_, y_, z_ = cones0[i]
    fig.add_trace(go.Mesh3d(x=x_, y=y_, z=z_, i=faces_i, j=faces_j, k=faces_k,
                            color='rgba(255,0,0,0.30)', flatshading=True,
                            lighting=dict(ambient=0.85, diffuse=0.15),
                            name=f"Wake-{i+1}", showlegend=False))
TOUCH_COLOR = 'rgb(102,217,255)'
for i in range(N_TURB):
    tx, ty, tz = touches0[i]
    fig.add_trace(go.Scatter3d(x=tx, y=ty, z=tz, mode='markers',
                               marker=dict(size=2.5, color=TOUCH_COLOR, opacity=0.9),
                               showlegend=False, name=f"Touch-{i+1}"))
fig.add_trace(bar0)

WAKE_START = 3
TOUCH_START = WAKE_START + N_TURB
BAR_INDEX = TOUCH_START + N_TURB
DYNAMIC_INDEXES = list(range(WAKE_START, BAR_INDEX+1))

frames = []
for d in tqdm(DIRS, desc="Build frames (3D by direction)"):
    cones, touches = build_wake_xyz(d, X_LEN_FIXED)
    updates = []
    for i in range(N_TURB):
        x_, y_, z_ = cones[i]
        updates.append(dict(type='mesh3d', x=x_, y=y_, z=z_))
    for i in range(N_TURB):
        tx, ty, tz = touches[i]
        updates.append(dict(type='scatter3d', x=tx, y=ty, z=tz))
    frames.append(go.Frame(name=f"d{d}", traces=DYNAMIC_INDEXES, data=updates))
fig.frames = frames

JS_PAYLOAD = dict(
    DIRS=DIRS, SPEEDS=SPEEDS_T15, INIT_DIR=INIT_DIR_DEG, INIT_U=INIT_T15,
    TID_ORDERED=TID_ORDERED, BAR_INDEX=BAR_INDEX, GRID=GRID, COUNTS=COUNTS,
    BAR_X_MAX=BAR_X_MAX, DIV_ID=DIV_ID, MIN_SAMPLES=MIN_SAMPLES
)

# ======================= 9) Figure layout =======================
FIG_HEIGHT = 740
fig.update_layout(
    height=FIG_HEIGHT,
    title='Speed Explorer',
    uirevision='keep',
    scene_dragmode="turntable",
    scene_camera=dict(center=dict(x=0, y=0, z=0),
                      eye=dict(x=1.5, y=1.5, z=0.7),
                      up=dict(x=0, y=0, z=1)),
    scene=dict(
        domain=dict(x=SCENE_DOMAIN_X, y=[0.0, 1.0]),
        aspectmode='data',
        xaxis_title='Easting [m]',
        yaxis_title='Northing [m]',
        zaxis_title='Elevation [m]'
    ),
    xaxis2=dict(domain=BAR_DOMAIN_X, anchor='y2', title='Wind speed (m/s)', range=[0, BAR_X_MAX]),
    yaxis2=dict(domain=[0.05, 0.95], anchor='x2', title='Turbine',
                type='category', categoryorder='array', categoryarray=JS_PAYLOAD["TID_ORDERED"],
                autorange='reversed'),
    margin=dict(l=0, r=0, t=58, b=10),
)

# ======================= 10) Build HTML with dual sliders and a toast banner =======================
html_fig = pio.to_html(
    fig, include_plotlyjs=True, full_html=False, div_id=DIV_ID,
    auto_play=False,
    config=dict(scrollZoom=True, displaylogo=False,
                doubleClick='reset', showTips=False)
)

payload = json.dumps(JS_PAYLOAD)

# Tick marks: wind direction every 30 deg, T15 speed every 2 m/s
dir_ticks_opt = "\n".join([f'<option value="{d}" label="{d}°"></option>' for d in range(0, 360, 30)])
dir_ticks_txt = "\n".join([f'<span>{d}°</span>' for d in range(0, 360, 30)])
spd_tick_min, spd_tick_max = JS_PAYLOAD["SPEEDS"][0], JS_PAYLOAD["SPEEDS"][-1]
spd_ticks_opt = "\n".join([f'<option value="{v}" label="{v}"></option>' for v in range(spd_tick_min, spd_tick_max+1, 2)])
spd_ticks_txt = "\n".join([f'<span>{v}</span>' for v in range(spd_tick_min, spd_tick_max+1, 2)])

html_tpl = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Speed Explorer</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  :root {{
    --wrap-max: 1680px;
    --slider-w: 480px;
  }}
  body {{ margin:0; font-family:Arial, Helvetica, sans-serif; }}
  .wrap {{ max-width: var(--wrap-max); margin: 10px auto 14px auto; }}
  /* Toast banner */
  #toast {{
    position: fixed; top: 10px; left: 50%; transform: translateX(-50%);
    background: rgba(255, 230, 180, 0.98);
    color: #333; border: 1px solid #f0b45e; border-radius: 8px;
    padding: 8px 14px; font-size: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    z-index: 9999; display: none;
  }}
  /* Control strip */
  .controls {{
    display:flex; flex-wrap:wrap; gap:32px; align-items:center;
    margin: 8px 10px 0 10px;
  }}
  .ctrl-block label {{ font-weight:600; margin-right:10px; white-space:nowrap; }}
  .ctrl-block .track {{ width: var(--slider-w); }}
  input[type=range] {{ width: 100%; }}
  .ticks {{ width: var(--slider-w); display:flex; justify-content:space-between;
            font-size:12px; color:#666; margin-top:2px; user-select:none; }}
  #{DIV_ID} {{ height: {FIG_HEIGHT}px; }}
</style>
</head>
<body>
<div id="toast"></div>

<div class="wrap">
  {html_fig}
  <div class="controls">
    <div class="ctrl-block">
      <label for="dirSlider">Wind direction:</label>
      <div class="track">
        <input id="dirSlider" type="range" min="0" max="355" step="{DIR_STEP_DEG}" value="{INIT_DIR_DEG}" list="ticksDir"/>
        <datalist id="ticksDir">{dir_ticks_opt}</datalist>
        <div class="ticks">{dir_ticks_txt}</div>
      </div>
      <span id="dirVal" class="small">{INIT_DIR_DEG}°</span>
    </div>
    <div class="ctrl-block">
      <label for="spdSlider">T15 wind speed:</label>
      <div class="track">
        <input id="spdSlider" type="range" min="{SPEEDS_T15[0]}" max="{SPEEDS_T15[-1]}" step="1" value="{INIT_T15}" list="ticksSpd"/>
        <datalist id="ticksSpd">{spd_ticks_opt}</datalist>
        <div class="ticks">{spd_ticks_txt}</div>
      </div>
      <span id="spdVal" class="small">{INIT_T15:.1f} m/s</span>
    </div>
  </div>
</div>

<script>
  const PL = {payload};  // {{DIRS, SPEEDS, INIT_DIR, INIT_U, TID_ORDERED, BAR_INDEX, GRID, COUNTS, BAR_X_MAX, DIV_ID, MIN_SAMPLES}}

  function snapToStep(v, step) {{ return Math.round(v/step)*step; }}

  function showToast(msg) {{
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.style.display = 'block';
    clearTimeout(window.__toastTimer);
    window.__toastTimer = setTimeout(() => {{ t.style.display = 'none'; }}, 2000);
  }}
  function hideToast() {{ document.getElementById('toast').style.display = 'none'; }}

  function updateBar(dir, u) {{
    const gridDir = PL.GRID[dir];
    if (!gridDir) return;
    const xs = gridDir[u];
    if (!xs) return;

    const texts = xs.map(v => v.toFixed(2) + " m/s");
    const gd = document.getElementById(PL.DIV_ID);
    Plotly.restyle(gd, {{ x: [xs], text: [texts], "marker.color":[xs] }}, [PL.BAR_INDEX]);

    // Only show a warning when the sample count falls below MIN_SAMPLES
    const cnt = (PL.COUNTS[dir] && PL.COUNTS[dir][u]) ? PL.COUNTS[dir][u] : 0;
    if (cnt < PL.MIN_SAMPLES) {{
      showToast(`Insufficient data for WD=${{dir}}?, T15=${{u}} m/s - N=${{cnt}} (< ${{PL.MIN_SAMPLES}})`);
    }} else {{
      hideToast();
    }}
  }}

  function animateDir(dir) {{
    const gd = document.getElementById(PL.DIV_ID);
    Plotly.animate(gd, [ "d"+String(dir) ], {{ frame: {{duration:0, redraw:true}}, mode: "immediate" }});
  }}

  (function init() {{
    const dirStep = {DIR_STEP_DEG};
    let curDir = PL.INIT_DIR;
    let curU   = PL.INIT_U;

    // Initial sync
    updateBar(curDir, curU);

    // Wind direction
    const dirSlider = document.getElementById('dirSlider');
    dirSlider.addEventListener('input', (e) => {{
      const d = snapToStep(parseInt(e.target.value,10), dirStep);
      e.target.value = d;
      document.getElementById('dirVal').textContent = d + "°";
      curDir = ((d%360)+360)%360;
      animateDir(curDir);
      updateBar(curDir, curU);
    }});

    // T15 wind speed
    const spdSlider = document.getElementById('spdSlider');
    spdSlider.addEventListener('input', (e) => {{
      curU = parseInt(e.target.value,10);
      document.getElementById('spdVal').textContent = curU.toFixed(1) + " m/s";
      updateBar(curDir, curU);
    }});
  }})();
</script>
</body>
</html>
"""

with open(OUT_HTML, "w", encoding="utf-8") as f:
    f.write(html_tpl)

print(f"Generated {OUT_HTML}")
