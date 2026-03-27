"""Generate the simplified U/V Component Chart used by the unified pack."""

import json
from glob import glob

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.utils import PlotlyJSONEncoder

from common_paths import OUTPUT_DIR, WIND_ROSE_CLEAN_DIR

TITLE = "U/V Component Chart"
OUT_HTML = OUTPUT_DIR / "wind_uv_anomalies_2023_offline.html"
PALETTE = [
    "#4c78a8", "#f58518", "#54a24b", "#e45756", "#9467bd", "#8c564b", "#e377c2",
    "#7f7f7f", "#b5bd00", "#64b5cd", "#4b4b8f", "#6b7d38", "#8c6d31", "#8c3d3d",
    "#7b4173", "#5b8cc0", "#a0c4de", "#e36a1a", "#4caf50", "#7e6dbf", "#6c6c6c",
]


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


def choose_time_col(df: pd.DataFrame) -> str:
    for col in ["wtc_CurTime_endvalue", "TimeStamp"]:
        if col in df.columns:
            return col
    raise ValueError("Could not find a timestamp column.")


def turbine_sort_key(label: str) -> int:
    digits = "".join(ch for ch in str(label) if ch.isdigit())
    return int(digits) if digits else 0


def load_scada() -> pd.DataFrame:
    files = sorted(glob(str(WIND_ROSE_CLEAN_DIR / "tblSCTurbine_2023_*_cleaned.csv")))
    if not files:
        raise FileNotFoundError(f"No cleaned monthly CSVs found in {WIND_ROSE_CLEAN_DIR}")

    frames = []
    for file_path in files:
        df = pd.read_csv(file_path, sep=None, engine="python")
        speed_col = choose_wind_speed_col(df)
        direction_col = choose_dir_col(df)
        time_col = choose_time_col(df)
        label_col = "label" if "label" in df.columns else None
        if label_col is None:
            raise ValueError(f"Missing 'label' column in {file_path}")

        sample = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(df[time_col], errors="coerce"),
                "label": df[label_col].astype(str).str.strip(),
                "wind_speed": pd.to_numeric(df[speed_col], errors="coerce"),
                "wind_direction": pd.to_numeric(df[direction_col], errors="coerce"),
            }
        )
        sample = sample.dropna(subset=["timestamp", "label", "wind_speed", "wind_direction"])
        sample = sample[(sample["wind_direction"] >= 0) & (sample["wind_direction"] <= 360)]
        frames.append(sample)

    data = pd.concat(frames, ignore_index=True)
    data = data[data["timestamp"].dt.year == 2023].copy()
    theta = np.deg2rad(data["wind_direction"].values)
    data["u"] = -data["wind_speed"].values * np.sin(theta)
    data["v"] = -data["wind_speed"].values * np.cos(theta)
    data["month_key"] = data["timestamp"].dt.strftime("%Y-%m")
    return data.sort_values(["timestamp", "label"]).reset_index(drop=True)


def build_month_figure(month_df: pd.DataFrame, month_key: str, color_map: dict[str, str]) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        subplot_titles=(
            f"{month_key} East-West Component (u)",
            f"{month_key} North-South Component (v)",
        ),
    )

    labels = sorted(month_df["label"].unique(), key=turbine_sort_key)
    for label in labels:
        dft = month_df[month_df["label"] == label]
        color = color_map[label]
        fig.add_trace(
            go.Scatter(
                x=dft["timestamp"],
                y=dft["u"],
                mode="lines",
                name=label,
                line=dict(color=color, width=1.3),
                legendgroup=label,
                showlegend=True,
                hovertemplate=f"Turbine: {label}<br>Time: %{{x}}<br>u: %{{y:.2f}} m/s<extra></extra>",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=dft["timestamp"],
                y=dft["v"],
                mode="lines",
                name=label,
                line=dict(color=color, width=1.3),
                legendgroup=label,
                showlegend=False,
                hovertemplate=f"Turbine: {label}<br>Time: %{{x}}<br>v: %{{y:.2f}} m/s<extra></extra>",
            ),
            row=2,
            col=1,
        )

    fig.update_layout(
        template="plotly",
        height=920,
        margin=dict(l=60, r=16, t=72, b=150),
        dragmode="zoom",
        legend=dict(
            title="Turbine",
            orientation="h",
            yanchor="bottom",
            y=-0.18,
            xanchor="left",
            x=0,
        ),
    )
    fig.update_xaxes(title="Timestamp", rangeslider=dict(visible=False), showspikes=True, fixedrange=False)
    fig.update_yaxes(title="East-West (u) [m/s]", row=1, col=1, fixedrange=False)
    fig.update_yaxes(title="North-South (v) [m/s]", row=2, col=1, fixedrange=False)
    return fig


def assemble_single_html(fig_map: dict[str, go.Figure], initial_key: str) -> str:
    keys = list(fig_map.keys())
    options = "\n".join(
        [f'<option value="{key}" {"selected" if key == initial_key else ""}>{key}</option>' for key in keys]
    )
    figure_payload = json.dumps(
        {key: fig.to_plotly_json() for key, fig in fig_map.items()},
        cls=PlotlyJSONEncoder,
    )
    plot_config = json.dumps(
        {
            "scrollZoom": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d", "autoScale2d"],
            "responsive": True,
        }
    )
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<title>{TITLE}</title>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  html, body {{ margin:0; background:#fff; }}
  body {{ font-family:Arial, Helvetica, sans-serif; color:#111827; }}
  .page {{ max-width:1820px; margin:10px auto; padding:0 12px 12px; }}
  .month-row {{ display:flex; gap:10px; align-items:center; margin:8px 0 6px 0; }}
  .hint {{ color:#7c8598; margin:4px 0 10px 0; }}
  #uvPlot {{ min-height:920px; }}
</style>
</head>
<body>
<div class="page">
  <h2 style="margin:6px 0;">{TITLE}</h2>
  <div class="month-row">
    <label for="monthSel"><b>Month:</b></label>
    <select id="monthSel">{options}</select>
  </div>
  <div class="hint">Scroll to zoom. Drag to pan.</div>
  <div id="uvPlot"></div>
</div>
<script src="https://cdn.plot.ly/plotly-3.4.0.min.js"></script>
<script>
  const MONTH_FIGS = {figure_payload};
  const PLOT_CONFIG = {plot_config};
  const DEFAULT_MARGIN = {{ l: 60, r: 16, t: 72, b: 150 }};
  const sel = document.getElementById('monthSel');
  const plotEl = document.getElementById('uvPlot');

  function cloneFigure(key) {{
    return JSON.parse(JSON.stringify(MONTH_FIGS[key]));
  }}

  function getTargetWidth() {{
    const page = document.querySelector('.page');
    return Math.max(
      980,
      Math.floor((page ? page.clientWidth : window.innerWidth) - 24)
    );
  }}

  function buildFigure(key) {{
    const figure = cloneFigure(key);
    const width = getTargetWidth();
    const layout = Object.assign({{}}, figure.layout || {{}});
    const margin = Object.assign({{}}, DEFAULT_MARGIN, layout.margin || {{}});
    layout.autosize = false;
    layout.width = width;
    layout.height = 920;
    layout.margin = margin;
    figure.layout = layout;
    plotEl.style.width = width + 'px';
    plotEl.style.height = '920px';
    return figure;
  }}

  function renderMonth(key) {{
    if (!window.Plotly || !MONTH_FIGS[key]) return Promise.resolve();
    const figure = buildFigure(key);
    const method = plotEl.dataset.ready === '1' ? 'react' : 'newPlot';
    return Plotly[method](plotEl, figure.data, figure.layout, PLOT_CONFIG)
      .then(() => {{
        plotEl.dataset.ready = '1';
        Plotly.Plots.resize(plotEl);
      }})
      .catch(() => {{}});
  }}

  sel.addEventListener('change', (e) => {{
    const key = e.target.value;
    renderMonth(key);
    requestAnimationFrame(() => renderMonth(key));
    setTimeout(() => renderMonth(sel.value), 120);
    setTimeout(() => renderMonth(sel.value), 320);
  }});

  window.addEventListener('load', () => {{
    renderMonth(sel.value);
    setTimeout(() => renderMonth(sel.value), 0);
    setTimeout(() => renderMonth(sel.value), 180);
    setTimeout(() => renderMonth(sel.value), 600);
  }});
  window.addEventListener('resize', () => setTimeout(() => renderMonth(sel.value), 60));
</script>
</body>
</html>"""

def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = load_scada()

    labels = sorted(data["label"].unique(), key=turbine_sort_key)
    color_map = {label: PALETTE[idx % len(PALETTE)] for idx, label in enumerate(labels)}

    fig_map: dict[str, go.Figure] = {}
    first_key = None
    for month_key in sorted(data["month_key"].unique()):
        month_df = data[data["month_key"] == month_key].copy()
        if month_df.empty:
            continue
        fig_map[month_key] = build_month_figure(month_df, month_key, color_map)
        if first_key is None:
            first_key = month_key

    if not fig_map or first_key is None:
        raise RuntimeError("No monthly U/V figures were generated.")

    OUT_HTML.write_text(assemble_single_html(fig_map, first_key), encoding="utf-8")
    print(f"Generated {OUT_HTML}")


if __name__ == "__main__":
    main()
