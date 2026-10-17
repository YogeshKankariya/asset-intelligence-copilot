"""Configuration and Path Resolution for Asset Intelligence Copilot."""

import os
from pathlib import Path

# 1. Reference Evaluation Date ("Today" in the official evaluation is 2027-01-15)
DEFAULT_EVALUATION_DATE = "2027-01-15"
REFERENCE_DATE = os.environ.get("EVALUATION_DATE", DEFAULT_EVALUATION_DATE)

# 2. Base dataset root determination
# Priority:
# a) Explicit DATASET_ROOT environment variable
# b) test-data/dataset if it exists
# c) flytbase-ahc-swe-asset-intelligence-dataset root
env_dataset_root = os.environ.get("DATASET_ROOT")
if env_dataset_root and Path(env_dataset_root).exists():
    DATASET_ROOT = Path(env_dataset_root)
else:
    candidate_test = Path(r"C:\Users\Admin\flytbase-ahc-swe-asset-intelligence-dataset\test-data\dataset")
    candidate_base = Path(r"C:\Users\Admin\flytbase-ahc-swe-asset-intelligence-dataset")
    if candidate_test.is_dir():
        DATASET_ROOT = candidate_test
    else:
        DATASET_ROOT = candidate_base


def resolve_assets_root(dataset_root: Path | None = None) -> Path:
    """Resolves the directory containing the asset folders (WELL-xxxx)."""
    root = dataset_root or DATASET_ROOT
    if (root / "assets").is_dir():
        return root / "assets"
    if os.environ.get("EVALUATION_MODE") == "1" or os.environ.get("DATASET_TYPE") == "test":
        if (root / "test-data" / "dataset" / "assets").is_dir():
            return root / "test-data" / "dataset" / "assets"
    if (root / "sample-data" / "assets").is_dir():
        return root / "sample-data" / "assets"
    if (root / "test-data" / "dataset" / "assets").is_dir():
        return root / "test-data" / "dataset" / "assets"
    return root / "assets"


def resolve_fleet_root(dataset_root: Path | None = None) -> Path:
    """Resolves the fleet directory containing areas.json, users.json, sops/, and well-types/."""
    root = dataset_root or DATASET_ROOT
    if (root / "fleet").is_dir():
        return root / "fleet"
    if os.environ.get("EVALUATION_MODE") == "1" or os.environ.get("DATASET_TYPE") == "test":
        if (root / "test-data" / "dataset" / "fleet").is_dir():
            return root / "test-data" / "dataset" / "fleet"
    if (root / "sample-data" / "fleet").is_dir():
        return root / "sample-data" / "fleet"
    if (root / "test-data" / "dataset" / "fleet").is_dir():
        return root / "test-data" / "dataset" / "fleet"
    return root / "fleet"


def resolve_asset_dir(asset_id: str, dataset_root: Path | None = None) -> Path:
    """Resolves the directory for a specific asset ID (e.g. WELL-0001)."""
    assets_root = resolve_assets_root(dataset_root)
    return assets_root / asset_id
