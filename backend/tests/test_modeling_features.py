"""Tests for feature engineering.

Verifies lag, rolling, temporal, and weather feature construction.
All features must be strictly causal (backward-looking only).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.modeling.features import (
    add_derived_features,
    add_lag_features,
    add_rolling_features,
    add_temporal_features,
    build_features,
    encode_wind,
)


def _make_weather_df(hours: int = 200) -> pd.DataFrame:
    """Create a deterministic hourly weather DataFrame."""
    idx = pd.date_range("2024-01-01", periods=hours, freq="1h", tz="UTC")
    t = np.arange(hours, dtype=float)
    df = pd.DataFrame(
        {
            "temperature_2m": 20 + 10 * np.sin(2 * np.pi * t / 24),
            "relative_humidity_2m": 60 + 20 * np.sin(2 * np.pi * t / 24 + np.pi),
            "wind_speed_10m": 5 + 3 * np.sin(2 * np.pi * t / 12),
            "wind_direction_10m": (180 + 90 * np.sin(2 * np.pi * t / 24)) % 360,
            "pressure_msl": 1013 + 5 * np.sin(2 * np.pi * t / 48),
            "precipitation": np.maximum(0, np.sin(2 * np.pi * t / 72) * 2),
        },
        index=idx,
    )
    df.index.name = "time"
    return df


class TestLagFeatures:
    """Tests for add_lag_features()."""

    def test_lag_columns_created(self) -> None:
        df = _make_weather_df(100)
        result = add_lag_features(df, columns=["temperature_2m"], lags=(1, 6))
        assert "temperature_2m_lag_1h" in result.columns
        assert "temperature_2m_lag_6h" in result.columns

    def test_lag_is_causal(self) -> None:
        df = _make_weather_df(100)
        result = add_lag_features(df, columns=["temperature_2m"], lags=(1,))
        # Lag at t=0 should be NaN (no data before)
        assert pd.isna(result["temperature_2m_lag_1h"].iloc[0])
        # Lag at t=1 should be the value at t=0
        assert result["temperature_2m_lag_1h"].iloc[1] == pytest.approx(
            df["temperature_2m"].iloc[0]
        )

    def test_no_negative_lags(self) -> None:
        df = _make_weather_df(50)
        result = add_lag_features(df, columns=["temperature_2m"], lags=(1,))
        # First row is NaN (no past data), rest should be non-NaN
        valid = result["temperature_2m_lag_1h"].dropna()
        assert len(valid) > 0

    def test_default_lags(self) -> None:
        df = _make_weather_df(100)
        result = add_lag_features(df, columns=["temperature_2m"])
        lag_cols = [c for c in result.columns if "_lag_" in c]
        assert len(lag_cols) >= 6  # at least the default lags


class TestRollingFeatures:
    """Tests for add_rolling_features()."""

    def test_rolling_columns_created(self) -> None:
        df = _make_weather_df(100)
        result = add_rolling_features(
            df, columns=["temperature_2m"], windows=(3, 6), operations=("mean",)
        )
        assert "temperature_2m_roll_3h_mean" in result.columns
        assert "temperature_2m_roll_6h_mean" in result.columns

    def test_rolling_mean_accuracy(self) -> None:
        df = _make_weather_df(10)
        result = add_rolling_features(
            df, columns=["temperature_2m"], windows=(3,), operations=("mean",)
        )
        # 3-hour rolling mean at row 2 should be mean of rows 0,1,2
        expected = df["temperature_2m"].iloc[:3].mean()
        assert result["temperature_2m_roll_3h_mean"].iloc[2] == pytest.approx(expected)

    def test_rolling_min_max(self) -> None:
        df = _make_weather_df(50)
        result = add_rolling_features(
            df, columns=["temperature_2m"], windows=(6,), operations=("min", "max")
        )
        assert "temperature_2m_roll_6h_min" in result.columns
        assert "temperature_2m_roll_6h_max" in result.columns
        # Min should be <= Max
        assert (result["temperature_2m_roll_6h_min"] <= result["temperature_2m_roll_6h_max"]).all()


class TestTemporalFeatures:
    """Tests for add_temporal_features()."""

    def test_hour_encoding(self) -> None:
        df = _make_weather_df(48)
        result = add_temporal_features(df, encode_hour=True)
        assert "hour_sin" in result.columns
        assert "hour_cos" in result.columns
        # Values should be in [-1, 1]
        assert result["hour_sin"].between(-1, 1).all()
        assert result["hour_cos"].between(-1, 1).all()

    def test_dow_encoding(self) -> None:
        df = _make_weather_df(168)  # 1 week
        result = add_temporal_features(df, encode_dow=True)
        assert "dow_sin" in result.columns
        assert "dow_cos" in result.columns

    def test_month_encoding(self) -> None:
        df = _make_weather_df(720)  # 30 days
        result = add_temporal_features(df, encode_month=True)
        assert "month_sin" in result.columns
        assert "month_cos" in result.columns

    def test_cyclical_continuity(self) -> None:
        """Hour 23 → Hour 0 should be close in sin/cos space."""
        idx = pd.date_range("2024-01-01", periods=25, freq="1h", tz="UTC")
        df = pd.DataFrame({"temperature_2m": range(25)}, index=idx)
        df.index.name = "time"
        result = add_temporal_features(df, encode_hour=True)
        # The sin/cos at hour 23 and hour 0 should be similar
        h23 = result[["hour_sin", "hour_cos"]].iloc[23]
        h0 = result[["hour_sin", "hour_cos"]].iloc[24]
        dist = np.sqrt(
            (h23["hour_sin"] - h0["hour_sin"]) ** 2 + (h23["hour_cos"] - h0["hour_cos"]) ** 2
        )
        assert dist < 0.3  # should be close

    def test_disabled_encodings(self) -> None:
        df = _make_weather_df(48)
        result = add_temporal_features(df, encode_hour=False, encode_dow=False, encode_month=False)
        assert "hour_sin" not in result.columns
        assert "dow_sin" not in result.columns
        assert "month_sin" not in result.columns


class TestWindEncoding:
    """Tests for encode_wind()."""

    def test_wind_components(self) -> None:
        df = _make_weather_df(50)
        result = encode_wind(df)
        assert "wind_dir_sin" in result.columns
        assert "wind_dir_cos" in result.columns
        # sin²+cos² ≈ 1
        mag = result["wind_dir_sin"] ** 2 + result["wind_dir_cos"] ** 2
        assert mag.round(6).between(0.999, 1.001).all()

    def test_north_wind(self) -> None:
        df = pd.DataFrame({"wind_direction_10m": [0], "wind_speed_10m": [5]})
        result = encode_wind(df)
        assert result["wind_dir_sin"].iloc[0] == pytest.approx(0.0, abs=1e-6)
        assert result["wind_dir_cos"].iloc[0] == pytest.approx(1.0, abs=1e-6)

    def test_missing_direction(self) -> None:
        df = pd.DataFrame({"wind_speed_10m": [5]})
        result = encode_wind(df)
        assert pd.isna(result["wind_dir_sin"].iloc[0])


class TestDerivedFeatures:
    """Tests for add_derived_features()."""

    def test_pressure_change(self) -> None:
        df = _make_weather_df(50)
        result = add_derived_features(df)
        assert "pressure_change" in result.columns
        # First value should be NaN (no previous)
        assert pd.isna(result["pressure_change"].iloc[0])
        # Second value should be diff
        expected = df["pressure_msl"].iloc[1] - df["pressure_msl"].iloc[0]
        assert result["pressure_change"].iloc[1] == pytest.approx(expected)

    def test_precipitation_accumulated(self) -> None:
        df = _make_weather_df(50)
        result = add_derived_features(df)
        assert "precipitation_accumulated_3h" in result.columns
        # 3-hour accumulation at row 2 should be sum of rows 0,1,2
        expected = df["precipitation"].iloc[:3].sum()
        assert result["precipitation_accumulated_3h"].iloc[2] == pytest.approx(expected)


class TestBuildFeatures:
    """Tests for the master build_features() function."""

    def test_full_pipeline(self) -> None:
        df = _make_weather_df(200)
        result = build_features(df)
        # Should have many more columns than input
        assert len(result.columns) > len(df.columns)

    def test_preserves_index(self) -> None:
        df = _make_weather_df(100)
        result = build_features(df)
        assert isinstance(result.index, pd.DatetimeIndex)
        assert len(result) == len(df)

    def test_deterministic(self) -> None:
        df = _make_weather_df(100)
        r1 = build_features(df)
        r2 = build_features(df)
        pd.testing.assert_frame_equal(r1, r2)
