"""Generate the offline 3D True Scale terrain view for the unified pack."""

from glob import glob

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import rasterio
from pyproj import Transformer
from rasterio.merge import merge
from rasterio.windows import from_bounds
from scipy.interpolate import RegularGridInterpolator

from common_paths import DEM_ROOT, META_CSV, OUTPUT_DIR

OUT_HTML = OUTPUT_DIR / "hill_of_towie_3d_true_scale.html"


def load_metadata() -> pd.DataFrame:
    df = pd.read_csv(META_CSV).rename(
        columns={
            "Turbine Name": "turbine_id",
            "Hub Height (m)": "hub_height",
            "Latitude": "latitude",
            "Longitude": "longitude",
        }
    )
    transformer = Transformer.from_crs(4326, 27700, always_xy=True)
    df["easting"], df["northing"] = transformer.transform(df["longitude"].values, df["latitude"].values)
    return df


def load_dem_window(x: np.ndarray, y: np.ndarray, buffer_m: float = 1000.0):
    xmin, xmax = x.min() - buffer_m, x.max() + buffer_m
    ymin, ymax = y.min() - buffer_m, y.max() + buffer_m

    asc_files = []
    for file_path in glob(str(DEM_ROOT / "**" / "*.asc"), recursive=True):
        with rasterio.open(file_path) as src:
            bounds = src.bounds
            if not (bounds.right < xmin or bounds.left > xmax or bounds.top < ymin or bounds.bottom > ymax):
                asc_files.append(file_path)

    if not asc_files:
        raise FileNotFoundError("No DEM .asc files were found inside the requested terrain window.")

    srcs = [rasterio.open(file_path) for file_path in asc_files]
    dem_full, tf_full = merge(srcs)
    win = from_bounds(xmin, ymin, xmax, ymax, tf_full)
    row_off, col_off = map(int, (win.row_off, win.col_off))
    height, width = map(int, (win.height, win.width))
    dem = dem_full[:, row_off : row_off + height, col_off : col_off + width]
    tf = rasterio.windows.transform(win, tf_full)
    return dem, tf


def interpolate_ground_z(dem: np.ndarray, tf, x: np.ndarray, y: np.ndarray):
    ys = np.arange(dem.shape[1]) * tf[4] + tf.f
    xs = np.arange(dem.shape[2]) * tf[0] + tf.c
    elev_fn = RegularGridInterpolator((ys[::-1], xs), dem[0, ::-1, :], bounds_error=False, fill_value=None)
    ground_z = elev_fn((y, x))
    return ground_z, xs, ys


def add_full_height_patch(html: str, div_id: str) -> str:
    patch = f"""
<style>
html, body {{
  margin: 0;
  height: 100%;
  overflow: hidden;
}}
body > div:first-of-type {{
  width: 100%;
  min-height: 100vh;
  height: 100vh;
}}
</style>
<script>
(function() {{
  const fig = document.getElementById('{div_id}');
  if (!fig || !window.Plotly) return;

  function resizeTrueScale() {{
    const targetH = Math.max(620, window.innerHeight - 12);
    const targetW = Math.max(480, window.innerWidth - 8);
    const root = document.body && document.body.firstElementChild;
    if (root) {{
      root.style.height = targetH + 'px';
      root.style.minHeight = targetH + 'px';
    }}
    fig.style.height = targetH + 'px';
    fig.style.minHeight = targetH + 'px';
    fig.style.width = targetW + 'px';
    try {{
      Plotly.relayout(fig, {{
        autosize: true,
        height: targetH,
        width: targetW,
        'margin.l': 0,
        'margin.r': 0,
        'margin.t': 36,
        'margin.b': 0,
        'scene.aspectmode': 'data',
        'scene.domain.x': [0, 1],
        'scene.domain.y': [0, 1]
      }});
      Plotly.Plots.resize(fig);
    }} catch (err) {{}}
  }}

  window.addEventListener('load', resizeTrueScale);
  window.addEventListener('resize', () => setTimeout(resizeTrueScale, 60));
  setTimeout(resizeTrueScale, 0);
  setTimeout(resizeTrueScale, 180);
  setTimeout(resizeTrueScale, 600);
}})();
</script>
"""
    return html.replace("</body>", patch + "\n</body>")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_metadata()
    x = df["easting"].values
    y = df["northing"].values
    hub_h = df["hub_height"].values

    dem, tf = load_dem_window(x, y)
    ground_z, xs, ys = interpolate_ground_z(dem, tf, x, y)
    hub_z = ground_z + hub_h
    xg, yg = np.meshgrid(xs, ys)

    fig = go.Figure()
    fig.add_trace(
        go.Surface(z=dem[0], x=xg, y=yg, colorscale="Earth", opacity=0.85, name="Terrain")
    )
    fig.add_trace(
        go.Scatter3d(
            x=x,
            y=y,
            z=hub_z,
            mode="markers+text",
            marker=dict(size=4, color="red"),
            text=df["turbine_id"],
            name="Turbine Hubs",
        )
    )
    fig.update_layout(
        title="3D True Scale",
        scene=dict(
            aspectmode="data",
            xaxis_title="Easting [m]",
            yaxis_title="Northing [m]",
            zaxis_title="Elevation [m]",
        ),
        margin=dict(l=0, r=0, b=0, t=40),
    )

    div_id = "true_scale_plot"
    html = pio.to_html(fig, include_plotlyjs=True, full_html=True, div_id=div_id)
    html = add_full_height_patch(html, div_id)
    OUT_HTML.write_text(html, encoding="utf-8")
    print(f"Generated {OUT_HTML}")


if __name__ == "__main__":
    main()
