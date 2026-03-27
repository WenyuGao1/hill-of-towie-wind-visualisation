"""Generate the offline Wind Rose module used by the unified Hill of Towie pack."""

import json
from glob import glob
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

from common_paths import OUTPUT_DIR, WIND_ROSE_CLEAN_DIR

DIR_BINS = 16
SPEED_BINS = (0, 2, 4, 6, 8, 10, 12, 15, 1e9)
SPEED_LABELS = ("0-2", "2-4", "4-6", "6-8", "8-10", "10-12", "12-15", "15+")
TITLE = "Annual Wind Rose (Cleaned, 2023)"
INITIAL_COLORED = True
OUT_HTML = OUTPUT_DIR / "annual_wind_rose_2023_interactive.html"


def choose_wind_speed_col(df: pd.DataFrame) -> str:
    for col in [
        "wtc_AcWindSp_mean",
        "wtc_PrWindSp_mean",
        "wtc_SeWindSp_mean",
        "wtc_SecAnemo_mean",
        "wtc_PriAnemo_mean",
    ]:
        if col in df.columns:
            return col
    raise ValueError("Could not find a wind speed column.")


def choose_dir_col(df: pd.DataFrame) -> str:
    if "wtc_ActualWindDirection_mean" in df.columns:
        return "wtc_ActualWindDirection_mean"
    raise ValueError("Could not find wtc_ActualWindDirection_mean.")


def load_annual_from_monthlies(monthly_dir: Path) -> pd.DataFrame:
    files = sorted(glob(str(monthly_dir / "tblSCTurbine_2023_*_cleaned.csv")))
    if not files:
        raise FileNotFoundError(f"No cleaned monthly CSVs found in {monthly_dir}")

    frames = []
    for file_path in files:
        df = pd.read_csv(file_path, sep=None, engine="python")
        speed_col = choose_wind_speed_col(df)
        direction_col = choose_dir_col(df)
        sample = pd.DataFrame(
            {
                "wind_speed": pd.to_numeric(df[speed_col], errors="coerce"),
                "wind_direction": pd.to_numeric(df[direction_col], errors="coerce"),
            }
        )
        sample.loc[
            (sample["wind_direction"] < 0) | (sample["wind_direction"] > 360),
            "wind_direction",
        ] = np.nan
        sample = sample.dropna(subset=["wind_speed", "wind_direction"])
        if not sample.empty:
            frames.append(sample)

    if not frames:
        raise RuntimeError("Monthly files exist, but no valid wind speed / direction rows were found.")
    return pd.concat(frames, ignore_index=True)


def mpl_default_colors(n: int) -> list[str]:
    base = plt.rcParams["axes.prop_cycle"].by_key().get("color", [])
    if not base:
        base = [
            "#1f77b4",
            "#ff7f0e",
            "#2ca02c",
            "#d62728",
            "#9467bd",
            "#8c564b",
            "#e377c2",
            "#7f7f7f",
            "#bcbd22",
            "#17becf",
        ]
    return [base[i % len(base)] for i in range(n)]


def compute_layer_sector_pct(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    sector_deg = 360.0 / DIR_BINS
    edges = np.arange(0, 360 + sector_deg, sector_deg)
    centers = edges[:-1] + sector_deg / 2
    total_n = len(df)

    layer_counts = []
    for idx in range(len(SPEED_BINS) - 1):
        lo, hi = SPEED_BINS[idx], SPEED_BINS[idx + 1]
        subset = df[(df["wind_speed"] >= lo) & (df["wind_speed"] < hi)]
        hist, _ = np.histogram(subset["wind_direction"].values % 360.0, bins=edges)
        layer_counts.append(hist.astype(float))

    layer_counts = np.array(layer_counts)
    layer_pct = layer_counts / max(total_n, 1) * 100.0
    sector_total_pct = layer_pct.sum(axis=0)
    return layer_pct, edges, centers, sector_total_pct


def make_interactive_wind_rose(df: pd.DataFrame) -> tuple[go.Figure, list[str]]:
    layer_pct, edges, centers, sector_total_pct = compute_layer_sector_pct(df)
    rmax = float(np.ceil(sector_total_pct.max() / 5.0) * 5.0)
    if rmax <= 0:
        rmax = 1.0

    sector_deg = 360.0 / DIR_BINS
    colors = mpl_default_colors(len(SPEED_LABELS))
    traces = []
    for idx, label in enumerate(SPEED_LABELS):
        customdata = np.vstack([edges[:-1], edges[1:], sector_total_pct]).T
        traces.append(
            go.Barpolar(
                r=layer_pct[idx],
                theta=centers,
                width=[sector_deg * 0.95] * len(centers),
                marker=dict(color=colors[idx]),
                name=label,
                customdata=customdata,
                hovertemplate=(
                    "<b>%{customdata[0]:.1f}?%{customdata[1]:.1f}?</b><br>"
                    "Speed bin: %{fullData.name}<br>"
                    "This layer: %{r:.1f}%<br>"
                    "Sector total: %{customdata[2]:.1f}%"
                    "<extra></extra>"
                ),
            )
        )

    tick_step = 5 if rmax >= 10 else 1
    tickvals = list(np.arange(0, rmax + 0.1, tick_step))

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=TITLE,
        paper_bgcolor="white",
        polar=dict(
            bgcolor="white",
            angularaxis=dict(direction="clockwise", rotation=90, gridcolor="lightgray"),
            radialaxis=dict(range=[0, rmax], ticks="outside", tickvals=tickvals, gridcolor="lightgray", angle=225),
        ),
        showlegend=False,
        margin=dict(l=40, r=40, t=60, b=40),
        barmode="stack",
        hovermode="closest",
    )
    return fig, colors


def build_controls(colors: list[str]) -> str:
    return f"""
<style>
html, body {{
  margin: 0;
  height: 100%;
  overflow: hidden;
}}
body > div:first-of-type {{
  width: 100%;
  min-height: 100vh;
}}
#wr-wrap {{
  display:flex; align-items:stretch; gap:16px; padding:8px 8px 8px 0;
  min-height: calc(100vh - 12px);
  height: calc(100vh - 12px);
}}
#windrose {{ flex:1 1 auto; min-width:0; min-height:100%; height:100% !important; }}
#wr-controls {{
  width:220px; background:#ffffff; border:1px solid #e5e7eb; border-radius:12px;
  padding:12px; box-shadow:0 6px 20px rgba(0,0,0,.08);
  font-family:Arial,sans-serif; color:#0f172a; position:relative; z-index:10;
  max-height: calc(100vh - 28px); overflow:auto;
}}
#wr-controls .group-title {{ font-weight:700; font-size:13px; margin:4px 0 8px; }}
#wr-controls .btn {{
  display:flex; align-items:center; width:100%; margin:8px 0; padding:10px 12px;
  border:1px solid #d1d5db; border-radius:10px; background:#f7f7f9; color:#0f172a;
  cursor:pointer; font-size:13px; line-height:1; opacity:1;
  transition:transform .12s ease, box-shadow .12s ease, background-color .12s ease, color .12s ease, border-color .12s ease;
}}
#wr-controls .btn:hover {{ transform: translateY(-1px); box-shadow:0 2px 6px rgba(0,0,0,.08); }}
#wr-controls .btn .swatch {{
  height:12px; width:12px; border-radius:3px; display:inline-block; margin-right:10px; flex:0 0 12px;
}}
#wr-controls .btn.active {{
  background: var(--btn-color); color:#ffffff; border-color:transparent; box-shadow:none; opacity:1;
  font-weight:600;
}}
#wr-controls .ops {{ display:flex; gap:8px; margin-bottom:6px; }}
#wr-controls .ops .op-btn {{
  flex:1 1 0; padding:8px 10px; border:1px solid #d1d5db; border-radius:10px; background:#ffffff; color:#0f172a;
  cursor:pointer; font-size:12px; opacity:1;
}}
#wr-controls .ops .op-btn:hover {{ box-shadow:0 2px 6px rgba(0,0,0,.08); transform: translateY(-1px); }}
</style>
<script>
(function(){{
  const fig = document.getElementById('windrose');
  const wrap = document.createElement('div'); wrap.id = 'wr-wrap';
  fig.parentNode.insertBefore(wrap, fig); wrap.appendChild(fig);

  const panel = document.createElement('div'); panel.id = 'wr-controls';
  wrap.appendChild(panel);

  const labels = {json.dumps(list(SPEED_LABELS))};
  const colors = {json.dumps(colors)};
  const n = labels.length;
  let vis = new Array(n).fill(true);

  const ops = document.createElement('div'); ops.className = 'ops';
  const showAll = document.createElement('button'); showAll.className = 'op-btn'; showAll.textContent = 'Show All';
  const hideAll = document.createElement('button'); hideAll.className = 'op-btn'; hideAll.textContent = 'Hide All';
  ops.appendChild(showAll); ops.appendChild(hideAll); panel.appendChild(ops);

  const title = document.createElement('div'); title.className = 'group-title';
  title.textContent = 'Wind Speed (m/s)'; panel.appendChild(title);

  const layerBtns = [];
  function makeBtn(idx) {{
    const button = document.createElement('button');
    button.className = 'btn';
    button.style.setProperty('--btn-color', colors[idx]);
    const swatch = document.createElement('span'); swatch.className = 'swatch'; swatch.style.background = colors[idx];
    const text = document.createElement('span'); text.textContent = labels[idx];
    button.appendChild(swatch); button.appendChild(text);
    button.onclick = function() {{
      vis[idx] = !vis[idx];
      Plotly.restyle(fig, {{ visible: vis[idx] }}, [idx]);
      updateButtons();
    }};
    panel.appendChild(button);
    return button;
  }}

  for (let i = 0; i < n; i += 1) layerBtns.push(makeBtn(i));

  function updateButtons() {{
    for (let i = 0; i < n; i += 1) {{
      if (vis[i] && {str(INITIAL_COLORED).lower()}) {{
        layerBtns[i].classList.add('active');
      }} else {{
        layerBtns[i].classList.remove('active');
      }}
    }}
  }}

  function resizeWindRose() {{
    const targetH = Math.max(620, window.innerHeight - 20);
    const targetW = Math.max(460, window.innerWidth - (panel.offsetWidth || 220) - 40);
    wrap.style.minHeight = targetH + 'px';
    wrap.style.height = targetH + 'px';
    fig.style.height = targetH + 'px';
    fig.style.minHeight = targetH + 'px';
    fig.style.width = targetW + 'px';
    panel.style.maxHeight = (targetH - 12) + 'px';
    try {{
      Plotly.relayout(fig, {{
        autosize: true,
        height: targetH,
        width: targetW,
        'margin.l': 18,
        'margin.r': 12,
        'margin.t': 34,
        'margin.b': 18,
        'polar.domain.x': [0.02, 0.98],
        'polar.domain.y': [0.02, 0.98]
      }});
      Plotly.Plots.resize(fig);
    }} catch (err) {{}}
  }}

  showAll.onclick = function() {{
    vis = vis.map(() => true);
    for (let i = 0; i < n; i += 1) Plotly.restyle(fig, {{ visible: true }}, [i]);
    updateButtons();
  }};
  hideAll.onclick = function() {{
    vis = vis.map(() => false);
    for (let i = 0; i < n; i += 1) Plotly.restyle(fig, {{ visible: false }}, [i]);
    updateButtons();
  }};

  updateButtons();
  window.addEventListener('load', resizeWindRose);
  window.addEventListener('resize', () => setTimeout(resizeWindRose, 60));
  setTimeout(resizeWindRose, 0);
  setTimeout(resizeWindRose, 180);
  setTimeout(resizeWindRose, 600);
}})();
</script>
"""


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_annual_from_monthlies(WIND_ROSE_CLEAN_DIR)
    fig, colors = make_interactive_wind_rose(df)
    html = pio.to_html(fig, include_plotlyjs=True, full_html=True, div_id="windrose")
    html = html.replace("</body>", build_controls(colors) + "\n</body>")
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Generated {OUT_HTML}")


if __name__ == "__main__":
    main()
