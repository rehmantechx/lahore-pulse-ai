"""Source Compass Phase 2 — Statistical Validation Script.

Runs all 11 analyses against the live database WITHOUT modifying production code.
Output is purely diagnostic.
"""

import random
import sqlite3
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "lahore_pulse.db"

SECTORS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
WINTER_MONTHS = {10, 11, 12, 1, 2, 3}
SPRING_MONTHS = {3, 4, 5}
SUMMER_MONTHS = {6, 7, 8}
AUTUMN_MONTHS = {9, 10, 11}


def deg_to_sector(degrees):
    idx = int((degrees + 22.5) / 45.0) % 8
    return SECTORS[idx]


def get_conn():
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA cache_size=-32000")
    return conn


def load_joined_data(winter_only=False, calm_filter_ms=None, pm25_threshold=120.0,
                     start_pct=0.0, end_pct=1.0):
    """Load wind+PM2.5 joined data with optional filters."""
    conn = get_conn()
    try:
        wind_rows = conn.execute("""
            SELECT d.observed_at, d.value,
                   s.value AS wind_speed
            FROM observations d
            LEFT JOIN observations s
              ON s.parameter = 'wind_speed_10m'
              AND s.observation_type = 'observation'
              AND s.observed_at = d.observed_at
            WHERE d.parameter = 'wind_direction_10m'
              AND d.observation_type = 'observation'
            ORDER BY d.observed_at ASC
        """).fetchall()

        pm25_rows = conn.execute("""
            SELECT observed_at, value
            FROM observations
            WHERE parameter = 'pm2_5'
              AND observation_type = 'observation'
            ORDER BY observed_at ASC
        """).fetchall()
    finally:
        conn.close()

    # Build PM2.5 lookup
    pm25_by_ts = {}
    for ts, val in pm25_rows:
        key = ts.replace("+00:00", "").replace("Z", "")
        pm25_by_ts[key] = val

    # Join
    joined = []
    for w_ts, direction, wind_speed in wind_rows:
        key = w_ts.replace("+00:00", "").replace("Z", "")
        pm25 = pm25_by_ts.get(key)
        if pm25 is None:
            continue
        try:
            dt = datetime.fromisoformat(key.replace("+00:00", ""))
            month = dt.month
        except (ValueError, TypeError):
            month = None
        joined.append({
            "ts": key,
            "pm25": pm25,
            "direction": direction,
            "wind_speed": wind_speed,
            "month": month,
            "is_episode": pm25 > pm25_threshold,
            "is_severe": pm25 > 150.0,
            "dt": dt,
        })

    # Apply time range filter (for time-dependence check)
    if start_pct > 0.0 or end_pct < 1.0:
        n = len(joined)
        start_idx = int(n * start_pct)
        end_idx = int(n * end_pct)
        joined = joined[start_idx:end_idx]

    # Apply calm filter
    if calm_filter_ms is not None:
        joined = [j for j in joined if j["wind_speed"] is not None and j["wind_speed"] >= calm_filter_ms]

    # Apply seasonal filter
    if winter_only:
        joined = [j for j in joined if j["month"] in WINTER_MONTHS]
    elif winter_only is False:
        pass  # all months

    return joined


def compute_sector_enrichment(joined):
    """Compute enrichment for all 8 sectors."""
    total = len(joined)
    if total == 0:
        return [], 0, 0

    total_episodes = sum(1 for j in joined if j["is_episode"])
    overall_rate = total_episodes / total

    stats = {}
    for s in SECTORS:
        stats[s] = {"count": 0, "episodes": 0, "severe": 0, "pm25_sum": 0.0}

    for j in joined:
        sector = deg_to_sector(j["direction"])
        stats[sector]["count"] += 1
        stats[sector]["pm25_sum"] += j["pm25"]
        if j["is_episode"]:
            stats[sector]["episodes"] += 1
        if j["is_severe"]:
            stats[sector]["severe"] += 1

    profile = []
    for s in SECTORS:
        c = stats[s]
        rate = c["episodes"] / c["count"] if c["count"] > 0 else 0
        enrichment = rate / overall_rate if overall_rate > 0 else 0
        avg_pm25 = c["pm25_sum"] / c["count"] if c["count"] > 0 else 0
        profile.append({
            "sector": s,
            "total_hours": c["count"],
            "episode_hours": c["episodes"],
            "severe_hours": c["severe"],
            "episode_rate": rate,
            "enrichment": enrichment,
            "avg_pm25": avg_pm25,
        })

    return profile, total_episodes, total


def print_sector_table(profile, total_episodes, total_hours, label=""):
    if label:
        print(f"\n{'='*80}")
        print(f"  {label}")
        print(f"{'='*80}")
    print(f"{'Sector':<8} {'Total':>8} {'Episodes':>10} {'Rate':>8} {'Enrich':>10} {'Avg PM2.5':>10} {'Severe':>8}")
    print("-" * 70)
    overall_rate = total_episodes / total_hours if total_hours > 0 else 0
    for p in sorted(profile, key=lambda x: x["enrichment"], reverse=True):
        marker = " ◄ STRONGEST" if p["sector"] == profile[0]["sector"] else ""
        # Only mark actual strongest by enrichment
        pass
    # Re-sort properly
    sorted_p = sorted(profile, key=lambda x: x["enrichment"], reverse=True)
    for p in sorted_p:
        marker = ""
        if p == sorted_p[0] and p["enrichment"] > 1.0:
            marker = " ◄ STRONGEST"
        print(f"{p['sector']:<8} {p['total_hours']:>8,} {p['episode_hours']:>10,} {p['episode_rate']:>8.4f} {p['enrichment']:>10.4f} {p['avg_pm25']:>10.1f} {p['severe_hours']:>8}{marker}")
    print(f"\nOverall rate: {overall_rate:.4f} ({total_episodes:,} episodes / {total_hours:,} total hours)")


def run_bootstrap(joined, n_resamples=2000, seed=42):
    """Episode-level bootstrap to test sector dominance stability."""
    random.seed(seed)

    # Group by episode (contiguous hours with same state)
    episodes = []
    current_ep = []
    for j in sorted(joined, key=lambda x: x["ts"]):
        if j["is_episode"]:
            current_ep.append(j)
        else:
            if current_ep:
                episodes.append(current_ep)
                current_ep = []
    if current_ep:
        episodes.append(current_ep)

    if not episodes:
        return {}

    ep_count = len(episodes)
    print(f"\nTotal independent episodes in joined data: {ep_count}")

    # Bootstrap: resample episodes with replacement
    sector_wins = defaultdict(int)
    sector_e_enrichment = []

    for _ in range(n_resamples):
        sample_eps = random.choices(episodes, k=ep_count)

        # Compute enrichment for this sample
        all_hours = []
        ep_hours = []
        for ep in sample_eps:
            for h in ep:
                all_hours.append(h)
                ep_hours.append(h)

        if not all_hours:
            continue

        # All observations (not just episodes) for rate calculation
        # We need the full context. For episode bootstrap, we compare
        # sector enrichment among episode hours only.
        total_sample = len(all_hours)
        ep_sample = len(ep_hours)

        # Count by sector in episode hours
        ep_sector_counts = defaultdict(int)
        for h in ep_hours:
            ep_sector_counts[deg_to_sector(h["direction"])] += 1

        # Find strongest sector by episode concentration
        if ep_sector_counts:
            strongest = max(ep_sector_counts, key=ep_sector_counts.get)
            sector_wins[strongest] += 1

            # Also compute actual enrichment for E in this sample
            # Need the full observation set for denominator
            # Use the original full dataset as denominator
            e_count = ep_sector_counts.get("E", 0)
            sector_e_enrichment.append(e_count)

    return {
        "ep_count": ep_count,
        "n_resamples": n_resamples,
        "sector_wins": dict(sector_wins),
        "sector_e_episode_hours": sector_e_enrichment,
    }


def main():
    print("=" * 80)
    print("  SOURCE COMPASS PHASE 2 — STATISTICAL VALIDATION")
    print("=" * 80)

    # ─── 1. DIRECTIONAL BASELINE (all months, all observations) ───
    print("\n" + "#" * 80)
    print("# 1. DIRECTIONAL BASELINE — ALL OBSERVATIONS")
    print("#" * 80)

    joined_all = load_joined_data(winter_only=None)
    profile_all, ep_all, total_all = compute_sector_enrichment(joined_all)
    print_sector_table(profile_all, ep_all, total_all,
                       "ALL MONTHS — Directional Baseline")

    # ─── 2. SEASONAL STABILITY ───
    print("\n" + "#" * 80)
    print("# 2. SEASONAL STABILITY")
    print("#" * 80)

    for season_name, months in [
        ("WINTER (Oct-Mar)", WINTER_MONTHS),
        ("SPRING (Mar-May)", SPRING_MONTHS),
        ("SUMMER (Jun-Aug)", SUMMER_MONTHS),
        ("AUTUMN (Sep-Nov)", AUTUMN_MONTHS),
    ]:
        conn = get_conn()
        try:
            wind_rows = conn.execute("""
                SELECT d.observed_at, d.value, s.value AS wind_speed
                FROM observations d
                LEFT JOIN observations s
                  ON s.parameter = 'wind_speed_10m' AND s.observation_type = 'observation' AND s.observed_at = d.observed_at
                WHERE d.parameter = 'wind_direction_10m' AND d.observation_type = 'observation'
                ORDER BY d.observed_at ASC
            """).fetchall()
            pm25_rows = conn.execute("""
                SELECT observed_at, value FROM observations
                WHERE parameter = 'pm2_5' AND observation_type = 'observation'
                ORDER BY observed_at ASC
            """).fetchall()
        finally:
            conn.close()

        pm25_by_ts = {ts.replace("+00:00", "").replace("Z", ""): val for ts, val in pm25_rows}
        season_joined = []
        for w_ts, direction, wind_speed in wind_rows:
            key = w_ts.replace("+00:00", "").replace("Z", "")
            pm25 = pm25_by_ts.get(key)
            if pm25 is None:
                continue
            try:
                dt = datetime.fromisoformat(key.replace("+00:00", ""))
                month = dt.month
            except:
                month = None
            if month in months:
                season_joined.append({
                    "ts": key, "pm25": pm25, "direction": direction,
                    "wind_speed": wind_speed, "month": month,
                    "is_episode": pm25 > 120.0, "is_severe": pm25 > 150.0, "dt": dt,
                })

        prof, ep_ct, tot = compute_sector_enrichment(season_joined)
        if tot > 0:
            print_sector_table(prof, ep_ct, tot, f"{season_name} ({len(season_joined):,} joined hours)")
        else:
            print(f"\n  {season_name}: No data")

    # Full period
    joined_full = load_joined_data(winter_only=None)
    prof_full, ep_full, tot_full = compute_sector_enrichment(joined_full)
    print_sector_table(prof_full, ep_full, tot_full, f"FULL PERIOD ({len(joined_full):,} joined hours)")

    # ─── 3. EPISODE ROBUSTNESS ───
    print("\n" + "#" * 80)
    print("# 3. EPISODE ROBUSTNESS — Episode hours only")
    print("#" * 80)

    # A. All observations
    joined_winter = load_joined_data(winter_only=True)
    prof_a, ep_a, tot_a = compute_sector_enrichment(joined_winter)
    print_sector_table(prof_a, ep_a, tot_a, "A. All winter observations")

    # B. Episode hours only
    ep_only = [j for j in joined_winter if j["is_episode"]]
    prof_b, ep_b, tot_b = compute_sector_enrichment(ep_only)
    # For episode-only, enrichment doesn't make sense the same way (every hour is an episode)
    # Instead show sector distribution
    if tot_b > 0:
        print(f"\n  B. SECTOR DISTRIBUTION OF EPISODE HOURS ({len(ep_only):,} episode-hours)")
        print(f"  {'Sector':<8} {'Episode Hours':>14} {'Share':>8}")
        print("  " + "-" * 34)
        sector_counts = defaultdict(int)
        for j in ep_only:
            sector_counts[deg_to_sector(j["direction"])] += 1
        for s in SECTORS:
            ct = sector_counts.get(s, 0)
            share = ct / len(ep_only) if ep_only else 0
            print(f"  {s:<8} {ct:>14,} {share:>8.4f}")

    # C. Severe episode hours (>150)
    severe_only = [j for j in joined_winter if j["is_severe"]]
    if severe_only:
        print(f"\n  C. SECTOR DISTRIBUTION OF SEVERE EPISODE HOURS ({len(severe_only):,} severe-hours)")
        print(f"  {'Sector':<8} {'Severe Hours':>14} {'Share':>8}")
        print("  " + "-" * 34)
        sector_counts_s = defaultdict(int)
        for j in severe_only:
            sector_counts_s[deg_to_sector(j["direction"])] += 1
        for s in SECTORS:
            ct = sector_counts_s.get(s, 0)
            share = ct / len(severe_only) if severe_only else 0
            print(f"  {s:<8} {ct:>14,} {share:>8.4f}")

    # ─── 4. EPISODE DOMINATION TEST ───
    print("\n" + "#" * 80)
    print("# 4. EPISODE DOMINATION TEST")
    print("#" * 80)

    # Find independent episodes, then count East contribution from each
    episodes = []
    current_ep = []
    for j in sorted(joined_winter, key=lambda x: x["ts"]):
        if j["is_episode"]:
            current_ep.append(j)
        else:
            if current_ep:
                episodes.append(current_ep)
                current_ep = []
    if current_ep:
        episodes.append(current_ep)

    print(f"  Total independent winter episodes: {len(episodes)}")

    # For each episode, count E-sector hours
    ep_e_contributions = []
    for i, ep in enumerate(episodes):
        e_hours = sum(1 for h in ep if deg_to_sector(h["direction"]) == "E")
        ep_e_contributions.append({
            "episode_idx": i,
            "episode_length": len(ep),
            "e_hours": e_hours,
            "start": ep[0]["ts"][:13],
            "end": ep[-1]["ts"][:13],
            "peak_pm25": max(h["pm25"] for h in ep),
        })

    # Sort by E contribution
    ep_e_contributions.sort(key=lambda x: x["e_hours"], reverse=True)
    total_e = sum(c["e_hours"] for c in ep_e_contributions)

    print(f"  Total E-sector episode-hours: {total_e}")
    print(f"  Number of episodes with E contribution: {sum(1 for c in ep_e_contributions if c['e_hours'] > 0)}")
    print(f"\n  Top 10 episodes contributing E-sector hours:")
    print(f"  {'Rank':<6} {'Start':<14} {'Length':>8} {'E Hours':>8} {'Peak PM2.5':>12} {'E Share':>8}")
    print("  " + "-" * 60)
    for rank, c in enumerate(ep_e_contributions[:10], 1):
        share = c["e_hours"] / total_e if total_e > 0 else 0
        print(f"  {rank:<6} {c['start']:<14} {c['episode_length']:>8} {c['e_hours']:>8} {c['peak_pm25']:>12.1f} {share:>8.4f}")

    # Concentration metrics
    if ep_e_contributions:
        top1_share = ep_e_contributions[0]["e_hours"] / total_e if total_e > 0 else 0
        top3_share = sum(c["e_hours"] for c in ep_e_contributions[:3]) / total_e if total_e > 0 else 0
        top5_share = sum(c["e_hours"] for c in ep_e_contributions[:5]) / total_e if total_e > 0 else 0
        e_contribs = [c["e_hours"] for c in ep_e_contributions if c["e_hours"] > 0]
        median_e = sorted(e_contribs)[len(e_contribs)//2] if e_contribs else 0
        print(f"\n  Concentration metrics:")
        print(f"    Top-1 episode: {top1_share:.1%} of all E hours")
        print(f"    Top-3 episodes: {top3_share:.1%} of all E hours")
        print(f"    Top-5 episodes: {top5_share:.1%} of all E hours")
        print(f"    Median E contribution per episode: {median_e} hours")
        print(f"    Episodes with ANY E contribution: {len(e_contribs)} of {len(episodes)}")

    # ─── 5. BOOTSTRAP STABILITY ───
    print("\n" + "#" * 80)
    print("# 5. BOOTSTRAP STABILITY — Episode-level resampling")
    print("#" * 80)

    bootstrap_result = run_bootstrap(joined_winter, n_resamples=2000, seed=42)
    if bootstrap_result:
        wins = bootstrap_result["sector_wins"]
        total = bootstrap_result["n_resamples"]
        print(f"\n  Bootstrap: {total} resamples of {bootstrap_result['ep_count']} episodes")
        print(f"  {'Sector':<8} {'Wins':>8} {'Frequency':>12}")
        print("  " + "-" * 32)
        for s in SECTORS:
            w = wins.get(s, 0)
            freq = w / total if total > 0 else 0
            print(f"  {s:<8} {w:>8} {freq:>12.4f}")

        e_wins = wins.get("E", 0)
        e_freq = e_wins / total if total > 0 else 0
        if e_freq >= 0.95:
            verdict = "ROBUST"
        elif e_freq >= 0.70:
            verdict = "MODERATELY STABLE"
        else:
            verdict = "UNSTABLE"
        print(f"\n  E-sector dominance: {e_freq:.1%} ({verdict})")

    # ─── 6. WIND-SPEED CONTROL ───
    print("\n" + "#" * 80)
    print("# 6. WIND-SPEED CONTROL")
    print("#" * 80)

    for label, calm_ms in [("All winds (no filter)", None), (">= 1.0 m/s", 1.0), (">= 1.5 m/s", 1.5), (">= 2.0 m/s", 2.0), (">= 3.0 m/s", 3.0)]:
        j = load_joined_data(winter_only=True, calm_filter_ms=calm_ms)
        prof, ep_ct, tot = compute_sector_enrichment(j)
        if tot > 0:
            strongest = max(prof, key=lambda p: p["enrichment"])
            print(f"\n  {label}: {tot:,} hours, {ep_ct:,} episodes")
            print(f"    Strongest: {strongest['sector']} ({strongest['enrichment']:.4f}x, {strongest['episode_hours']} ep-hours)")
            # Print all
            for p in sorted(prof, key=lambda x: x["enrichment"], reverse=True):
                print(f"      {p['sector']}: {p['enrichment']:.4f}x ({p['episode_hours']}/{p['total_hours']})")
        else:
            print(f"\n  {label}: No data")

    # ─── 7. THRESHOLD SENSITIVITY ───
    print("\n" + "#" * 80)
    print("# 7. THRESHOLD SENSITIVITY")
    print("#" * 80)

    for label, threshold in [("PM2.5 > 80 (elevated)", 80.0), ("PM2.5 > 120 (episode)", 120.0), ("PM2.5 > 150 (severe)", 150.0), ("PM2.5 > 200 (extreme)", 200.0)]:
        joined_th = load_joined_data(winter_only=True, pm25_threshold=threshold)
        # Override is_episode
        for j in joined_th:
            j["is_episode"] = j["pm25"] > threshold
        prof, ep_ct, tot = compute_sector_enrichment(joined_th)
        if tot > 0:
            strongest = max(prof, key=lambda p: p["enrichment"])
            print(f"\n  {label}: {tot:,} hours, {ep_ct:,} episodes")
            print(f"    Strongest: {strongest['sector']} ({strongest['enrichment']:.4f}x, {strongest['episode_hours']} ep-hours)")
            for p in sorted(prof, key=lambda x: x["enrichment"], reverse=True):
                marker = " ◄" if p["sector"] == strongest["sector"] else ""
                print(f"      {p['sector']}: {p['enrichment']:.4f}x ({p['episode_hours']}/{p['total_hours']}){marker}")
        else:
            print(f"\n  {label}: No data")

    # ─── 8. TIME-DEPENDENCE CHECK ───
    print("\n" + "#" * 80)
    print("# 8. TIME-DEPENDENCE CHECK")
    print("#" * 80)

    joined_full_w = load_joined_data(winter_only=True)
    n = len(joined_full_w)
    thirds = n // 3

    for label, start, end in [
        ("Early third", 0, thirds),
        ("Middle third", thirds, 2 * thirds),
        ("Recent third", 2 * thirds, n),
    ]:
        subset = joined_full_w[start:end]
        prof, ep_ct, tot = compute_sector_enrichment(subset)
        if tot > 0:
            strongest = max(prof, key=lambda p: p["enrichment"])
            ts_start = subset[0]["ts"][:13] if subset else "?"
            ts_end = subset[-1]["ts"][:13] if subset else "?"
            print(f"\n  {label} ({ts_start} to {ts_end}): {tot:,} hours, {ep_ct:,} episodes")
            print(f"    Strongest: {strongest['sector']} ({strongest['enrichment']:.4f}x)")
            for p in sorted(prof, key=lambda x: x["enrichment"], reverse=True)[:3]:
                print(f"      {p['sector']}: {p['enrichment']:.4f}x ({p['episode_hours']}/{p['total_hours']})")
        else:
            print(f"\n  {label}: No data")

    # ─── 9. WINTER ENRICHMENT WITH FULL SECTOR TABLE ───
    print("\n" + "#" * 80)
    print("# 9. WINTER ENRICHMENT — FINAL TABLE (This is the production signal)")
    print("#" * 80)

    joined_w = load_joined_data(winter_only=True)
    prof_w, ep_w, tot_w = compute_sector_enrichment(joined_w)
    print_sector_table(prof_w, ep_w, tot_w, f"WINTER ONLY ({len(joined_w):,} joined hours)")

    print("\n" + "=" * 80)
    print("  VALIDATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
