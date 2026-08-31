"""Synthetic transaction and recovery scenario engine package."""

from data.synthetic.cli import compute_dataset_hash, serialize_dataset_for_hashing
from data.synthetic.generator import SyntheticDataGenerator
from data.synthetic.models import (
    CustomerProfileType,
    DatasetStatistics,
    GeneratorConfig,
    ObservableDataset,
    RecoveryGroundTruth,
    ScenarioType,
    SyntheticDataset,
    ValidationResult,
)
from data.synthetic.profiles import PROFILES, ProfileConfig
from data.synthetic.scenarios import SCENARIO_SPECS, ScenarioSpec
from data.synthetic.seeder import seed_dataset_to_database
from data.synthetic.statistics import calculate_statistics
from data.synthetic.validator import DatasetValidator

__all__ = [
    "SyntheticDataGenerator",
    "DatasetValidator",
    "calculate_statistics",
    "seed_dataset_to_database",
    "compute_dataset_hash",
    "serialize_dataset_for_hashing",
    "GeneratorConfig",
    "CustomerProfileType",
    "ScenarioType",
    "RecoveryGroundTruth",
    "ObservableDataset",
    "SyntheticDataset",
    "DatasetStatistics",
    "ValidationResult",
    "PROFILES",
    "ProfileConfig",
    "SCENARIO_SPECS",
    "ScenarioSpec",
]
