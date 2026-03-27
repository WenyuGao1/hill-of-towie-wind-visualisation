"""Shared project-relative paths for the module generators."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "github project_wind"

WIND_ROSE_CLEAN_DIR = PROJECT_ROOT / "Dissertation" / "dataset" / "wind_rose" / "cleaned_csv"

SCOTLAND_ROOT = PROJECT_ROOT / "Dissertation" / "dataset" / "Scotland-Hill-of-Towie"
SCOTLAND_DATASET_DIR = SCOTLAND_ROOT / "dataset"
SCOTLAND_OUTCOME_DIR = SCOTLAND_ROOT / "outcome" / "2023"

META_CSV = SCOTLAND_DATASET_DIR / "Hill_of_Towie_turbine_metadata.csv"
DEM_ROOT = SCOTLAND_DATASET_DIR / "nj"

MODEL_ZIP = PROJECT_ROOT / "Dissertation" / "generic-wind-turbine-v136-1255h-145d.zip"
MODEL_MEMBER = "source/125_5h145d.dae"


def find_scada_raw_dir() -> Path:
    """Return the first matching 2023 raw SCADA directory inside the repository."""
    candidates = sorted(SCOTLAND_DATASET_DIR.glob("hill_towie_2023*"))
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("Could not locate the 2023 Hill of Towie raw SCADA directory.")
