"""End-to-end pipeline test with real collected data.

Loads observations from the database, builds the full modeling dataset,
and generates the quality report. This verifies the entire Phase 2 pipeline
works with real Open-Meteo data.
"""

from __future__ import annotations

import sys
from datetime import date

import pandas as pd

sys.path.insert(0, ".")

from app.core.config import Settings
from app.infrastructure.database import Database
from app.modeling.collector import DataCollector
from app.modeling.config import DatasetConfig, SplitConfig
from app.modeling.dataset import DatasetBuilder
from app.modeling.report import generate_markdown_report, generate_json_report


def main() -> None:
    settings = Settings()
    db_path = settings.database_url.replace("sqlite:///", "")
    db = Database(db_path)

    print("=" * 70)
    print("Lahore Pulse AI — End-to-End Pipeline Test (Real Data)")
    print("=" * 70)

    # 1. Load observations from DB
    collector = DataCollector(settings, db)
    raw_rows = collector.load_observations()
    print(f"\n1. Loaded {len(raw_rows):,} raw observations from database")

    if not raw_rows:
        print("   ❌ No observations found! Run collect_real_data.py first.")
        return

    # 2. Pivot to wide format
    df = pd.DataFrame(raw_rows)
    # Mixed formats: old data has "+00:00" suffix, new data doesn't
    # Normalize by stripping timezone suffix, then parse flexibly
    df["observed_at"] = df["observed_at"].str.replace(r"\+00:00$", "", regex=True)
    # Pad short timestamps to include seconds: "T00:00" -> "T00:00:00"
    df["observed_at"] = df["observed_at"].str.replace(
        r"T(\d{2}:\d{2})$", r"T\1:00", regex=True
    )
    df["observed_at"] = pd.to_datetime(df["observed_at"])
    df = df.set_index("observed_at")

    pivot = df.pivot_table(
        values="value",
        index=df.index,
        columns="parameter",
        aggfunc="first",
    )
    pivot.index.name = "time"
    print(f"2. Pivoted to wide format: {pivot.shape[0]} rows × {pivot.shape[1]} columns")
    print(f"   Columns: {list(pivot.columns)}")

    # 3. Check PM2.5 availability
    if "pm2_5" in pivot.columns:
        pm25_valid = pivot["pm2_5"].dropna()
        print(f"3. PM2.5 target: {len(pm25_valid):,} valid observations out of {len(pivot):,}")
        print(f"   Missing ratio: {pivot['pm2_5'].isna().mean():.2%}")
        print(f"   Mean: {pm25_valid.mean():.2f} µg/m³")
        print(f"   Range: {pm25_valid.min():.2f} – {pm25_valid.max():.2f} µg/m³")
    else:
        print("3. ❌ No PM2_5 column found!")
        return

    # 4. Build the dataset
    print(f"\n4. Running DatasetBuilder pipeline...")
    config = DatasetConfig(
        splits=SplitConfig(gap_hours=24, min_train_hours=500),
    )
    builder = DatasetBuilder(config=config)
    bundle = builder.build_from_dataframe(pivot)

    # 5. Report results
    print(f"\n5. Pipeline Results:")
    print(f"   Full dataset: {bundle.full_dataset.shape[0]} rows × {bundle.full_dataset.shape[1]} columns")
    print(f"   Train: {bundle.train.shape[0]} rows")
    print(f"   Validation: {bundle.validation.shape[0]} rows")
    print(f"   Test: {bundle.test.shape[0]} rows")
    print(f"   Quality score: {bundle.quality_report.quality_score:.3f}")
    print(f"   Leakage checks: {'PASSED' if bundle.leakage_report.get('passed') else 'FAILED'}")
    print(f"   Total leakage errors: {bundle.leakage_report.get('total_errors', 0)}")

    # 6. Target columns
    target_cols = [c for c in bundle.full_dataset.columns if c.startswith("target_")]
    feature_cols = [c for c in bundle.full_dataset.columns if not c.startswith("target_")]
    print(f"\n6. Feature columns: {len(feature_cols)}")
    print(f"   Target columns: {len(target_cols)}")

    # Leakage diagnostics
    print(f"\n6b. Leakage diagnostics:")
    for check_name, check_data in bundle.leakage_report.get("checks", {}).items():
        n_errors = len(check_data.get("errors", []))
        status = "PASS" if check_data.get("passed") else "FAIL"
        print(f"   - {check_name}: {status} ({n_errors} errors)")
        # Print first 3 errors for debugging
        for err in check_data.get("errors", [])[:3]:
            print(f"     → {err}")
        if n_errors > 3:
            print(f"     ... and {n_errors - 3} more")

    for tc in target_cols:
        valid = bundle.full_dataset[tc].dropna()
        print(f"   - {tc}: {len(valid):,} valid / {len(bundle.full_dataset):,} total")

    # 7. Generate reports
    print(f"\n7. Generating reports...")
    md_report = generate_markdown_report(bundle)
    json_report = generate_json_report(bundle)

    with open("PHASE2_REPORT.md", "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"   ✅ PHASE2_REPORT.md written ({len(md_report):,} chars)")

    import json
    with open("PHASE2_REPORT.json", "w", encoding="utf-8") as f:
        json.dump(json_report, f, indent=2, default=str)
    print(f"   ✅ PHASE2_REPORT.json written")

    db.close()
    print(f"\n{'=' * 70}")
    print("End-to-end pipeline test COMPLETE!")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
