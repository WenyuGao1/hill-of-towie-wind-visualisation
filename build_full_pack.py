"""Build the four module HTML files and then rebuild the unified offline pack."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GEN_DIR = ROOT / "module_generators"

MODULE_SCRIPTS = [
    "build_wind_rose.py",
    "build_uv_component_chart.py",
    "build_true_scale.py",
    "build_speed_explorer.py",
]


def run_script(script: Path) -> None:
    print(f"Running {script.name} ...")
    subprocess.run([sys.executable, str(script)], cwd=ROOT, check=True)


def main() -> None:
    for name in MODULE_SCRIPTS:
        run_script(GEN_DIR / name)
    run_script(ROOT / "main.py")
    print("Build completed.")


if __name__ == "__main__":
    main()
