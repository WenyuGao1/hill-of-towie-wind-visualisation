# Hill of Towie Wind Visualisation

An offline-first wind-farm visualisation project that turns SCADA measurements, turbine metadata, and terrain context into a compact multi-view presentation.

This lightweight repository is the portfolio version of the project: it keeps the cleaned source code, the active module outputs, and the pack builder, while staying inside normal GitHub file-size limits.

## Online Demo

- GitHub Pages homepage: [https://wenyugao1.github.io/hill-of-towie-wind-visualisation/](https://wenyugao1.github.io/hill-of-towie-wind-visualisation/)
- Direct module views:
  - [Wind Rose](https://wenyugao1.github.io/hill-of-towie-wind-visualisation/?view=annual_wind_rose_2023_interactive.html)
  - [U/V Component Chart](https://wenyugao1.github.io/hill-of-towie-wind-visualisation/?view=wind_uv_anomalies_2023_offline.html)
  - [3D True Scale](https://wenyugao1.github.io/hill-of-towie-wind-visualisation/?view=hill_of_towie_3d_true_scale.html)
  - [Speed Explorer](https://wenyugao1.github.io/hill-of-towie-wind-visualisation/?view=hill_of_towie_interactive_speed.html)

## Project Highlights

- Built four coordinated visualisation modules for wind-farm analysis
- Refactored a research-style prototype into a cleaner, reproducible codebase
- Packaged multiple HTML views into a single `Pack.html` workflow
- Preserved an offline presentation path while also preparing a GitHub-friendly lightweight version

## Standalone HTML Files In This Repo

- [Wind Rose](./github%20project_wind/annual_wind_rose_2023_interactive.html)
- [U/V Component Chart](./github%20project_wind/wind_uv_anomalies_2023_offline.html)
- [3D True Scale](./github%20project_wind/hill_of_towie_3d_true_scale.html)
- [Speed Explorer](./github%20project_wind/hill_of_towie_interactive_speed.html)

## Unified Pack Overview

The public lightweight repository keeps the modular HTML demos, while the full local workflow can still be bundled into a single Pack interface like this:

<p align="center">
  <img src="./assets/screenshots/pack-overview.png" alt="Unified Pack overview screenshot" width="100%">
</p>

## Screenshots

<table>
<tr>
<td width="50%" align="center"><strong>Wind Rose</strong><br><img src="./assets/screenshots/wind-rose.png" alt="Wind Rose screenshot" width="100%"></td>
<td width="50%" align="center"><strong>U/V Component Chart</strong><br><img src="./assets/screenshots/uv-component-chart.png" alt="U/V Component Chart screenshot" width="100%"></td>
</tr>
<tr>
<td width="50%" align="center"><strong>3D True Scale</strong><br><img src="./assets/screenshots/true-scale.png" alt="3D True Scale screenshot" width="100%"></td>
<td width="50%" align="center"><strong>Speed Explorer</strong><br><img src="./assets/screenshots/speed-explorer.png" alt="Speed Explorer screenshot" width="100%"></td>
</tr>
</table>


## Active Modules

### 1. Wind Rose

Interactive annual wind-direction and wind-speed distribution view.

### 2. U/V Component Chart

Monthly east-west and north-south wind component time series, simplified to remove anomaly-report presentation.

### 3. 3D True Scale

Terrain-aligned 3D turbine layout using DEM-derived elevation data.

### 4. Speed Explorer

Terrain-aware 3D wind-speed exploration view with directional and turbine-level interaction.

## Tech Stack

- Python
- Pandas and NumPy
- Plotly
- Rasterio and PyProj
- Trimesh

## Repository Layout

```text
github_light/
|-- .nojekyll
|-- assets/
|   `-- screenshots/
|       |-- pack-overview.png
|       |-- wind-rose.png
|       |-- uv-component-chart.png
|       |-- true-scale.png
|       `-- speed-explorer.png
|-- module_generators/
|   |-- build_wind_rose.py
|   |-- build_uv_component_chart.py
|   |-- build_true_scale.py
|   |-- build_speed_explorer.py
|   `-- common_paths.py
|-- github project_wind/
|   |-- annual_wind_rose_2023_interactive.html
|   |-- wind_uv_anomalies_2023_offline.html
|   |-- hill_of_towie_3d_true_scale.html
|   `-- hill_of_towie_interactive_speed.html
|-- main.py
|-- build_full_pack.py
|-- index.html
|-- requirements.txt
`-- README.md
```

## What This Lightweight Version Includes

- The active source code for the four module generators
- The current standalone module HTML outputs
- A GitHub Pages-ready root entry in `index.html`
- The pack builder in `main.py`
- A structure suitable for a normal GitHub repository without Git LFS

## What It Intentionally Omits

- The large dissertation-era raw datasets
- The full offline `Pack.html` artifact
- The heavyweight rebuild inputs required by `build_full_pack.py`

This means:

- You can open the included module HTML files directly
- You can run `python main.py` to rebuild a local `Pack.html` from the included module HTML files
- You cannot fully regenerate every module from raw data using this lightweight repo alone

## Install

```powershell
pip install -r requirements.txt
```

## Rebuild The Pack From Included Module HTML Files

```powershell
python main.py
```

The rebuilt `Pack.html` in this lightweight version depends on the Plotly CDN because the included demo HTML files are the lightweight web-friendly variants.

## Portfolio Framing

This repository is intended to demonstrate:

- applied data visualisation work
- offline HTML packaging
- technical refactoring of a messy prototype
- careful trimming of a large local project into a clean public-facing portfolio repository
