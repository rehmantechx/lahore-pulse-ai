"""Dataset configuration — immutable config objects for the modeling pipeline.

Defines all tunables for target construction, feature engineering,
temporal alignment, and dataset splitting.  Every downstream component
receives a frozen config so behaviour is reproducible and auditable.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ── Forecasting Problem Definition ───────────────────────────────────
#
# We forecast PM2.5 concentration (μg/m³) at Lahore city center
# (31.5204°N, 74.3587°E) using hourly meteorological and air-quality
# observations.
#
# Mathematical formulation:
#   Given X(t) = {x₁(t), x₂(t), …, xₙ(t)}  (feature vector at time t)
#   Predict   y(t+h) = PM2.5 concentration h hours ahead
#
# Supported horizons (hours): 1, 3, 6, 12, 24
# ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class TargetConfig:
    """Configuration for the forecast target variable.

    Attributes:
        parameter: The observation parameter to forecast.
        unit: Expected unit of the target.
        horizons_hours: Future horizons to predict (in hours).
        max_missing_ratio: Maximum allowed fraction of NaN in the target
                           series before the dataset is rejected.
        outlier_zscore_threshold: Z-score above which a target value
                                  is flagged as an outlier.
    """

    parameter: str = "pm2_5"
    unit: str = "ug/m3"
    horizons_hours: tuple[int, ...] = (1, 3, 6, 12, 24)
    max_missing_ratio: float = 0.10
    outlier_zscore_threshold: float = 4.0


# ── Feature Engineering Configuration ────────────────────────────────


@dataclass(frozen=True)
class LagConfig:
    """Lag-feature configuration.

    Attributes:
        offsets: Lag offsets in hours.  A lag of k means x(t-k).
    """

    offsets: tuple[int, ...] = (1, 2, 3, 6, 12, 24, 48, 72)


@dataclass(frozen=True)
class RollingConfig:
    """Rolling-window feature configuration.

    Attributes:
        windows: Window sizes in hours.
        operations: Aggregation functions to apply.
    """

    windows: tuple[int, ...] = (3, 6, 12, 24)
    operations: tuple[str, ...] = ("mean", "std", "min", "max")


@dataclass(frozen=True)
class TemporalFeatureConfig:
    """Cyclical time-of-day / day-of-week encoding.

    Attributes:
        encode_hour: Include sin/cos hour-of-day features.
        encode_dow: Include sin/cos day-of-week features.
        encode_month: Include sin/cos month-of-year features.
    """

    encode_hour: bool = True
    encode_dow: bool = True
    encode_month: bool = True


@dataclass(frozen=True)
class WeatherFeatureConfig:
    """Raw meteorological feature selection.

    Attributes:
        variables: Open-Meteo variable names to include as raw features.
        wind_encode: Encode wind as (speed, sin(dir), cos(dir)) triple.
        derived: Include derived features (heat_index, etc.).
    """

    variables: tuple[str, ...] = (
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "apparent_temperature",
        "precipitation",
        "rain",
        "cloud_cover",
        "pressure_msl",
        "surface_pressure",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "shortwave_radiation",
        "vapour_pressure_deficit",
        "soil_temperature_0_to_7cm",
        "soil_moisture_0_to_7cm",
    )
    wind_encode: bool = True
    derived: bool = True


@dataclass(frozen=True)
class FeatureConfig:
    """Aggregate feature-engineering configuration.

    Groups lag, rolling, temporal, and weather sub-configs.
    """

    lags: LagConfig = field(default_factory=LagConfig)
    rolling: RollingConfig = field(default_factory=RollingConfig)
    temporal: TemporalFeatureConfig = field(default_factory=TemporalFeatureConfig)
    weather: WeatherFeatureConfig = field(default_factory=WeatherFeatureConfig)


# ── Temporal Alignment ───────────────────────────────────────────────


@dataclass(frozen=True)
class AlignmentConfig:
    """Controls how observations are aligned to a regular time grid.

    Attributes:
        freq: Target frequency string (pandas-compatible).
        timezone: IANA timezone for display; storage is always UTC.
        max_gap_hours: Largest gap (in hours) to fill via forward-fill.
                       Gaps larger than this are left as NaN.
    """

    freq: str = "1h"
    timezone: str = "Asia/Karachi"
    max_gap_hours: int = 3


# ── Dataset Splitting ────────────────────────────────────────────────


@dataclass(frozen=True)
class SplitConfig:
    """Chronological train / validation / test split configuration.

    Attributes:
        train_ratio: Fraction of data for training.
        val_ratio:   Fraction of data for validation.
        test_ratio:  Fraction of data for testing (must sum to 1.0).
        gap_hours:   Buffer between train/val and val/test to prevent
                     any temporal leakage through lag features.
        min_train_hours: Minimum training set size in hours.
    """

    train_ratio: float = 0.70
    val_ratio: float = 0.15
    test_ratio: float = 0.15
    gap_hours: int = 72  # 3-day buffer
    min_train_hours: int = 720  # 30 days minimum

    def __post_init__(self) -> None:
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 1e-6:
            msg = f"Split ratios must sum to 1.0, got {total}"
            raise ValueError(msg)


# ── Data Collection ──────────────────────────────────────────────────


@dataclass(frozen=True)
class CollectionConfig:
    """Configuration for data collection from Open-Meteo APIs.

    Attributes:
        latitude:  Location latitude.
        longitude: Location longitude.
        weather_lookback_days: Days of historical weather to collect.
        aq_lookback_days: Days of historical AQ to collect.
        weather_variables: Weather variables to fetch.
        aq_variables: Air quality variables to fetch.
        timezone: Timezone string for API responses.
    """

    latitude: float = 31.5204
    longitude: float = 74.3587
    weather_lookback_days: int = 60
    aq_lookback_days: int = 60
    weather_variables: tuple[str, ...] = (
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "apparent_temperature",
        "precipitation",
        "rain",
        "cloud_cover",
        "pressure_msl",
        "surface_pressure",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "shortwave_radiation",
        "vapour_pressure_deficit",
        "soil_temperature_0_to_7cm",
        "soil_moisture_0_to_7cm",
    )
    aq_variables: tuple[str, ...] = (
        "pm10",
        "pm2_5",
        "nitrogen_dioxide",
        "sulphur_dioxide",
        "ozone",
        "carbon_monoxide",
    )
    timezone: str = "UTC"


# ── Master Dataset Config ────────────────────────────────────────────


@dataclass(frozen=True)
class DatasetConfig:
    """Top-level configuration combining all sub-configs.

    This is the single source of truth for the entire modeling pipeline.
    All downstream components receive this (or a sub-config) at construction.
    """

    target: TargetConfig = field(default_factory=TargetConfig)
    features: FeatureConfig = field(default_factory=FeatureConfig)
    alignment: AlignmentConfig = field(default_factory=AlignmentConfig)
    splits: SplitConfig = field(default_factory=SplitConfig)
    collection: CollectionConfig = field(default_factory=CollectionConfig)

    # Versioning — bump when config changes break reproducibility
    schema_version: str = "1.0.0"

    @property
    def all_feature_names(self) -> list[str]:
        """Enumerate all feature columns the pipeline can produce."""
        names: list[str] = []

        # Weather features
        for var in self.features.weather.variables:
            names.append(var)
        if self.features.weather.wind_encode:
            names.extend(["wind_dir_sin", "wind_dir_cos"])

        # Lag features
        for var in self.features.weather.variables:
            for lag in self.features.lags.offsets:
                names.append(f"{var}_lag_{lag}h")

        # Rolling features
        for var in self.features.weather.variables:
            for window in self.features.rolling.windows:
                for op in self.features.rolling.operations:
                    names.append(f"{var}_roll_{window}h_{op}")

        # Temporal features
        if self.features.temporal.encode_hour:
            names.extend(["hour_sin", "hour_cos"])
        if self.features.temporal.encode_dow:
            names.extend(["dow_sin", "dow_cos"])
        if self.features.temporal.encode_month:
            names.extend(["month_sin", "month_cos"])

        # PM2.5 lag features (target-derived features)
        for lag in self.features.lags.offsets:
            names.append(f"pm2_5_lag_{lag}h")

        return names
