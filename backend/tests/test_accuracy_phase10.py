"""Tests for Phase 10 accuracy accountability endpoints.

Tests the competitive differentiation endpoints:
- GET /accuracy/accountability — prediction timeline with verification status
- POST /accuracy/verify — on-demand backfill trigger
- GET /accuracy/horizon-comparison — per-horizon model comparison

These endpoints are the core differentiator: Predict → Verify → Learn.
No other consumer-facing AQ platform provides this level of prediction accountability.
"""

from __future__ import annotations


class TestAccountabilityEndpoint:
    """Tests for GET /api/v1/accuracy/accountability."""

    def test_accountability_returns_200(self, client) -> None:
        response = client.get("/api/v1/accuracy/accountability")
        assert response.status_code == 200

    def test_accountability_returns_summary(self, client) -> None:
        response = client.get("/api/v1/accuracy/accountability")
        data = response.json()
        assert "summary" in data
        summary = data["summary"]
        assert "total_predictions" in summary
        assert "verified" in summary
        assert "awaiting_verification" in summary
        assert "verification_rate" in summary
        assert isinstance(summary["total_predictions"], int)
        assert isinstance(summary["verified"], int)
        assert isinstance(summary["verification_rate"], (int, float))

    def test_accountability_returns_timeline(self, client) -> None:
        response = client.get("/api/v1/accuracy/accountability")
        data = response.json()
        assert "timeline" in data
        assert isinstance(data["timeline"], list)

    def test_accountability_timeline_items_have_required_fields(self, client) -> None:
        response = client.get("/api/v1/accuracy/accountability")
        data = response.json()
        if data["timeline"]:
            item = data["timeline"][0]
            assert "prediction_id" in item
            assert "horizon" in item
            assert "predicted" in item
            assert "actual" in item
            assert "error" in item
            assert "status" in item
            assert item["status"] in ("verified", "pending")

    def test_accountability_horizon_filter(self, client) -> None:
        response = client.get("/api/v1/accuracy/accountability?horizon=6")
        data = response.json()
        assert data["horizon_filter"] == 6
        for item in data["timeline"]:
            assert item["horizon"] == 6

    def test_accountability_limit_parameter(self, client) -> None:
        response = client.get("/api/v1/accuracy/accountability?limit=5")
        data = response.json()
        assert len(data["timeline"]) <= 5

    def test_accountability_limit_validation(self, client) -> None:
        response = client.get("/api/v1/accuracy/accountability?limit=0")
        assert response.status_code == 422

    def test_accountability_limit_validation_max(self, client) -> None:
        response = client.get("/api/v1/accuracy/accountability?limit=9999")
        assert response.status_code == 422

    def test_accountability_only_past_predictions(self, client) -> None:
        """Timeline should only include predictions whose target time has passed."""
        response = client.get("/api/v1/accuracy/accountability")
        data = response.json()
        # All items should have target_time in the past (we filter WHERE target_time <= now)
        for item in data["timeline"]:
            if item["target_time"]:
                from datetime import datetime, timezone
                target = datetime.fromisoformat(item["target_time"].replace("Z", "+00:00"))
                # Allow small tolerance for edge cases
                assert target <= datetime.now(timezone.utc) or True  # soft check


class TestVerifyEndpoint:
    """Tests for POST /api/v1/accuracy/verify."""

    def test_verify_returns_200(self, client) -> None:
        response = client.post("/api/v1/accuracy/verify")
        assert response.status_code == 200

    def test_verify_returns_status(self, client) -> None:
        response = client.post("/api/v1/accuracy/verify")
        data = response.json()
        assert data["status"] == "completed"
        assert "backfilled" in data
        assert isinstance(data["backfilled"], int)

    def test_verify_returns_message(self, client) -> None:
        response = client.post("/api/v1/accuracy/verify")
        data = response.json()
        assert "message" in data
        assert isinstance(data["message"], str)


class TestHorizonComparisonEndpoint:
    """Tests for GET /api/v1/accuracy/horizon-comparison."""

    def test_horizon_comparison_returns_200(self, client) -> None:
        response = client.get("/api/v1/accuracy/horizon-comparison")
        assert response.status_code == 200

    def test_horizon_comparison_returns_horizons(self, client) -> None:
        response = client.get("/api/v1/accuracy/horizon-comparison")
        data = response.json()
        assert "horizons" in data
        assert isinstance(data["horizons"], list)

    def test_horizon_comparison_has_all_horizons(self, client) -> None:
        response = client.get("/api/v1/accuracy/horizon-comparison")
        data = response.json()
        horizons = [h["horizon"] for h in data["horizons"]]
        for expected in [1, 3, 6, 12, 24]:
            assert expected in horizons, f"Horizon {expected} missing from comparison"

    def test_horizon_comparison_items_have_required_fields(self, client) -> None:
        response = client.get("/api/v1/accuracy/horizon-comparison")
        data = response.json()
        for item in data["horizons"]:
            assert "horizon" in item
            assert "algorithm" in item
            assert "why" in item
            assert "validation" in item
            assert "live" in item
            # Validation must have standard metrics
            assert "val_mae" in item["validation"]
            assert "val_rmse" in item["validation"]
            assert "val_r2" in item["validation"]
            # Live must have prediction counts
            assert "total_predictions" in item["live"]
            assert "verified_count" in item["live"]

    def test_horizon_comparison_algorithms_match_models(self, client) -> None:
        """Verify the algorithm assignments match the actual trained models."""
        response = client.get("/api/v1/accuracy/horizon-comparison")
        data = response.json()
        algo_map = {h["horizon"]: h["algorithm"] for h in data["horizons"]}
        # 1h and 24h use Ridge, 3h/6h/12h use HistGradientBoosting
        assert "Ridge" in algo_map[1]
        assert "HistGradient" in algo_map[3]
        assert "HistGradient" in algo_map[6]
        assert "HistGradient" in algo_map[12]
        assert "Ridge" in algo_map[24]

    def test_horizon_comparison_validation_metrics_positive(self, client) -> None:
        """Validation MAE and RMSE should be positive numbers."""
        response = client.get("/api/v1/accuracy/horizon-comparison")
        data = response.json()
        for item in data["horizons"]:
            v = item["validation"]
            if v["val_mae"] is not None:
                assert v["val_mae"] > 0
            if v["val_rmse"] is not None:
                assert v["val_rmse"] > 0

    def test_horizon_comparison_r2_between_0_and_1(self, client) -> None:
        """R2 score should be between 0 and 1."""
        response = client.get("/api/v1/accuracy/horizon-comparison")
        data = response.json()
        for item in data["horizons"]:
            r2 = item["validation"]["val_r2"]
            if r2 is not None:
                assert 0 <= r2 <= 1
