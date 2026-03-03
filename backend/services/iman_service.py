"""
Iman Index Service — Behavioral logging, computation, and trajectory analysis.

Module-level functions (matching source_service.py pattern).
Implements Steps 1-8 of the Iman Index algorithm from IMAN_INDEX_ARCHITECTURE.md.
"""

import math
import statistics
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from data.iman_behaviors import (
    ALL_BEHAVIOR_IDS,
    BASE_WEIGHTS,
    BEHAVIOR_MAP,
    DEFAULT_BEHAVIORS,
    HEART_NOTE_TYPES,
    HEART_STATES,
    IMAN_BEHAVIORS,
    IMAN_CATEGORIES,
)
from data.iman_heart_states import HEART_STATE_MAP, ALL_HEART_STATE_IDS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CALIBRATION_DAYS = 14          # Days before baseline is established
RECALIBRATION_INTERVAL = 30    # Days between baseline recalibrations
EMA_OLD_WEIGHT = 0.7           # Exponential moving average: weight for old baseline
EMA_NEW_WEIGHT = 0.3           # EMA: weight for recent data
PILLAR_ALPHA = 0.25            # Performance weight in category composite
PILLAR_BETA = 0.45             # Consistency weight (highest — Atomic Habits principle)
PILLAR_GAMMA = 0.30            # Trajectory weight
ENGINE_VERSION = "1.0"

# Strain/Recovery constants
STRAIN_DIFFICULTY = {
    "binary": 1.0,
    "scale_5": 1.2,
    "minutes": 1.0,
    "hours": 1.0,
    "count": 0.8,
    "count_inv": 1.3,
}
SR_RESTORATIVE_UPPER = 0.8
SR_BALANCED_UPPER = 1.3
SR_HIGH_STRAIN_UPPER = 2.0
SR_BURNOUT_CONSECUTIVE_DAYS = 7

# Safeguard thresholds
SCRUPULOSITY_TAWBAH_STREAK_DAYS = 7
EMERGENCY_CONSECUTIVE_DAYS = 7
HUMILITY_RESET_FRACTION = 30   # Deterministic: hash(uid+date) % 30 == 0
REDUCED_JOURNAL_RECAL_DAYS = 14
REDUCED_JOURNAL_BEHAVIORS = ["fajr_prayer", "quran_minutes", "dhikr_minutes"]


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_behavior_value(behavior_id: str, value) -> Tuple[bool, str, Any]:
    """Validate a behavior log value against its input_type.

    Returns (is_valid, error_message, coerced_value).
    """
    behavior = BEHAVIOR_MAP.get(behavior_id)
    if not behavior:
        return False, f"Unknown behavior: {behavior_id}", None

    input_type = behavior["input_type"]

    try:
        if input_type == "binary":
            v = int(value)
            if v not in (0, 1):
                return False, f"{behavior_id}: binary must be 0 or 1", None
            return True, "", v

        if input_type == "scale_5":
            v = int(value)
            if not 0 <= v <= 5:
                return False, f"{behavior_id}: scale must be 0-5", None
            return True, "", v

        if input_type == "minutes":
            v = float(value)
            if v < 0 or v > 1440:
                return False, f"{behavior_id}: minutes must be 0-1440", None
            return True, "", round(v, 1)

        if input_type == "hours":
            v = float(value)
            if v < 0 or v > 24:
                return False, f"{behavior_id}: hours must be 0-24", None
            return True, "", round(v, 1)

        if input_type == "count":
            v = int(value)
            if v < 0 or v > 100:
                return False, f"{behavior_id}: count must be 0-100", None
            return True, "", v

        if input_type == "count_inv":
            v = int(value)
            if v < 0 or v > 100:
                return False, f"{behavior_id}: count must be 0-100", None
            return True, "", v

        return False, f"{behavior_id}: unknown input_type {input_type}", None

    except (TypeError, ValueError):
        return False, f"{behavior_id}: invalid value {value!r}", None


HEART_NOTE_LIMITS = {
    "gratitude": 280,
    "dua": 280,
    "tawbah": 280,
    "connection": 280,
    "reflection": 500,
    "quran_insight": 500,
}


def validate_heart_note(note_type: str, text: str) -> Tuple[bool, str]:
    """Validate heart note type and text (type-dependent char limit)."""
    if note_type not in HEART_NOTE_TYPES:
        return False, f"Invalid heart note type: {note_type}. Must be one of: {HEART_NOTE_TYPES}"
    if not text or not text.strip():
        return False, "Heart note text cannot be empty"
    max_len = HEART_NOTE_LIMITS.get(note_type, 280)
    if len(text) > max_len:
        return False, f"Heart note too long: {len(text)} chars (max {max_len})"
    return True, ""


def validate_heart_state(state: str) -> Tuple[bool, str]:
    """Validate heart state selection."""
    if state not in HEART_STATES:
        return False, f"Invalid heart state: {state}. Must be one of: {HEART_STATES}"
    return True, ""


# ---------------------------------------------------------------------------
# Setup / Config
# ---------------------------------------------------------------------------

def build_default_config(behavior_ids: Optional[List[str]] = None) -> dict:
    """Build initial iman_config/settings document.

    If behavior_ids provided, use those. Otherwise use DEFAULT_BEHAVIORS.
    """
    if behavior_ids:
        # Validate all IDs exist
        invalid = [bid for bid in behavior_ids if bid not in BEHAVIOR_MAP]
        if invalid:
            raise ValueError(f"Unknown behavior IDs: {invalid}")
        behaviors = [BEHAVIOR_MAP[bid] for bid in behavior_ids]
    else:
        behaviors = DEFAULT_BEHAVIORS

    tracked = []
    now = datetime.now(timezone.utc).isoformat()
    for b in behaviors:
        tracked.append({
            "id": b["id"],
            "category": b["category"],
            "label": b["label"],
            "input_type": b["input_type"],
            "weight_override": None,
            "active": True,
            "added_at": now,
        })

    return {
        "tracked_behaviors": tracked,
        "baseline_period_start": now,
        "baseline_established": False,
        "onboarding_complete": True,
        "engine_version": ENGINE_VERSION,
    }


def get_tracked_behavior_ids(config: dict) -> List[str]:
    """Extract list of active behavior IDs from a config document."""
    return [
        b["id"] for b in config.get("tracked_behaviors", [])
        if b.get("active", True)
    ]


# ---------------------------------------------------------------------------
# Step 1: Behavior Normalization
# ---------------------------------------------------------------------------

def normalize_behavior_value(behavior_id: str, raw_value, p95: float = None) -> float:
    """Normalize a raw behavior value to [0, 1] per input_type rules.

    For minutes/count/count_inv, p95 is the user's 95th percentile (personal ceiling).
    If p95 is None, sensible defaults are used.
    """
    behavior = BEHAVIOR_MAP.get(behavior_id)
    if not behavior:
        return 0.0

    input_type = behavior["input_type"]

    try:
        v = float(raw_value)
    except (TypeError, ValueError):
        return 0.0

    if input_type == "binary":
        return 1.0 if v >= 1 else 0.0

    if input_type == "scale_5":
        return min(max(v / 5.0, 0.0), 1.0)

    if input_type == "minutes":
        p95_safe = max(p95 or 30.0, 1.0)
        return min(v / p95_safe, 1.0)

    if input_type == "hours":
        # Gaussian centered at 7.5h, sigma 1.5 — optimal sleep
        return math.exp(-0.5 * ((v - 7.5) / 1.5) ** 2)

    if input_type == "count":
        p95_safe = max(p95 or 10.0, 1.0)
        return min(v / p95_safe, 1.0)

    if input_type == "count_inv":
        # Fewer is better (e.g., anger incidents)
        p95_safe = max(p95 or 5.0, 1.0)
        return max(1.0 - (v / p95_safe), 0.0)

    return 0.0


# ---------------------------------------------------------------------------
# Step 2: Category Aggregation
# ---------------------------------------------------------------------------

def aggregate_category_scores(
    behaviors_logged: Dict[str, Any],
    tracked_ids: List[str],
    p95_values: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Compute daily category scores from logged behaviors.

    Returns {category_id: score} where score is [0, 1].
    Missing behaviors count as 0 for binary/scale, excluded for hours.
    """
    p95s = p95_values or {}
    category_values: Dict[str, List[float]] = defaultdict(list)

    for bid in tracked_ids:
        behavior = BEHAVIOR_MAP.get(bid)
        if not behavior:
            continue

        cat = behavior["category"]
        raw = behaviors_logged.get(bid)

        if raw is None:
            # Missing data handling
            if behavior["input_type"] == "hours":
                continue  # Don't penalize for not logging sleep
            category_values[cat].append(0.0)
        else:
            # Extract value — raw might be {value: X, logged_at: ...} or just X
            if isinstance(raw, dict):
                val = raw.get("value", 0)
            else:
                val = raw
            normalized = normalize_behavior_value(bid, val, p95s.get(bid))
            category_values[cat].append(normalized)

    # Compute mean per category
    result = {}
    for cat_id in IMAN_CATEGORIES:
        values = category_values.get(cat_id, [])
        if values:
            result[cat_id] = sum(values) / len(values)
        else:
            result[cat_id] = 0.0

    return result


# ---------------------------------------------------------------------------
# Step 3: Baseline Computation
# ---------------------------------------------------------------------------

def _median(values: List[float]) -> float:
    """Median of a list. Returns 0 for empty list."""
    if not values:
        return 0.0
    return statistics.median(values)


def _mad(values: List[float]) -> float:
    """Median Absolute Deviation. Robust alternative to std_dev."""
    if len(values) < 2:
        return 0.1  # Minimum sensible MAD
    med = statistics.median(values)
    deviations = [abs(v - med) for v in values]
    return max(statistics.median(deviations), 0.05)  # Floor at 0.05


def _percentile(values: List[float], pct: float) -> float:
    """Simple percentile calculation."""
    if not values:
        return 0.0
    sorted_v = sorted(values)
    idx = (len(sorted_v) - 1) * pct / 100.0
    lower = int(math.floor(idx))
    upper = int(math.ceil(idx))
    if lower == upper:
        return sorted_v[lower]
    frac = idx - lower
    return sorted_v[lower] * (1 - frac) + sorted_v[upper] * frac


def compute_baselines(
    daily_category_scores: List[Dict[str, float]],
    existing_baselines: Optional[dict] = None,
) -> dict:
    """Compute or recalibrate baselines from daily category score history.

    daily_category_scores: list of {category: score} dicts, one per day.
    existing_baselines: if provided, does EMA blend (recalibration).
    Returns baselines document for Firestore.
    """
    now = datetime.now(timezone.utc).isoformat()
    baselines = {}

    for cat_id in IMAN_CATEGORIES:
        values = [d.get(cat_id, 0.0) for d in daily_category_scores]
        values = [v for v in values if v is not None]

        if not values:
            baselines[cat_id] = {
                "median": 0.0,
                "mean": 0.0,
                "std_dev": 0.1,
                "mad": 0.1,
                "p95": 1.0,
                "sample_size": 0,
                "updated_at": now,
            }
            continue

        new_median = _median(values)
        new_mean = sum(values) / len(values)
        new_std = statistics.stdev(values) if len(values) >= 2 else 0.1
        new_mad = _mad(values)
        new_p95 = _percentile(values, 95)

        if existing_baselines and cat_id in existing_baselines:
            old = existing_baselines[cat_id]
            # EMA blend: 0.7 old + 0.3 new
            baselines[cat_id] = {
                "median": EMA_OLD_WEIGHT * old.get("median", 0) + EMA_NEW_WEIGHT * new_median,
                "mean": EMA_OLD_WEIGHT * old.get("mean", 0) + EMA_NEW_WEIGHT * new_mean,
                "std_dev": EMA_OLD_WEIGHT * old.get("std_dev", 0.1) + EMA_NEW_WEIGHT * new_std,
                "mad": EMA_OLD_WEIGHT * old.get("mad", 0.1) + EMA_NEW_WEIGHT * new_mad,
                "p95": EMA_OLD_WEIGHT * old.get("p95", 1.0) + EMA_NEW_WEIGHT * new_p95,
                "sample_size": len(values),
                "updated_at": now,
            }
        else:
            # Fresh baseline (initial calibration)
            baselines[cat_id] = {
                "median": new_median,
                "mean": new_mean,
                "std_dev": max(new_std, 0.05),
                "mad": new_mad,
                "p95": max(new_p95, 0.1),
                "sample_size": len(values),
                "updated_at": now,
            }

    baselines["last_recalibration"] = now
    return baselines


# ---------------------------------------------------------------------------
# Step 4: Three Pillars (Performance, Consistency, Trajectory)
# ---------------------------------------------------------------------------

def _pearson_r(x: List[float], y: List[float]) -> float:
    """Compute Pearson correlation coefficient between two lists.

    Returns 0.0 if insufficient data or zero variance.
    """
    n = min(len(x), len(y))
    if n < 3:
        return 0.0

    x, y = x[:n], y[:n]
    mean_x = sum(x) / n
    mean_y = sum(y) / n

    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    var_x = sum((xi - mean_x) ** 2 for xi in x)
    var_y = sum((yi - mean_y) ** 2 for yi in y)

    denom = math.sqrt(var_x * var_y)
    if denom < 1e-10:
        return 0.0
    return cov / denom


# ---------------------------------------------------------------------------
# Cross-Behavior Correlation Detection
# ---------------------------------------------------------------------------

MIN_CORRELATION_DATA_POINTS = 14
MIN_CORRELATION_THRESHOLD = 0.40


def compute_behavior_correlations(
    daily_logs: List[dict],
    tracked_ids: List[str],
    window_days: int = 30,
) -> List[dict]:
    """Compute Pearson correlations across all behavior pairs.

    Uses last `window_days` of logs. Filters for |r| > 0.40, min 14 points.
    Returns list sorted by |r| descending.
    """
    recent = daily_logs[-window_days:] if len(daily_logs) > window_days else daily_logs

    # Build per-behavior time series
    behavior_series: Dict[str, List[Tuple[int, float]]] = defaultdict(list)
    for i, log in enumerate(recent):
        behaviors = log.get("behaviors", {})
        for bid in tracked_ids:
            raw = behaviors.get(bid)
            if raw is not None:
                val = raw.get("value", raw) if isinstance(raw, dict) else raw
                normalized = normalize_behavior_value(bid, val)
                behavior_series[bid].append((i, normalized))

    # Filter to behaviors with enough data
    eligible = [bid for bid in tracked_ids if len(behavior_series.get(bid, [])) >= MIN_CORRELATION_DATA_POINTS]

    correlations = []
    for i, bid_a in enumerate(eligible):
        for bid_b in eligible[i + 1:]:
            series_a = behavior_series[bid_a]
            series_b = behavior_series[bid_b]

            # Align by day index
            dates_a = {d: v for d, v in series_a}
            dates_b = {d: v for d, v in series_b}
            common = sorted(set(dates_a) & set(dates_b))

            if len(common) < MIN_CORRELATION_DATA_POINTS:
                continue

            x = [dates_a[d] for d in common]
            y = [dates_b[d] for d in common]
            r = _pearson_r(x, y)

            if abs(r) >= MIN_CORRELATION_THRESHOLD:
                label_a = BEHAVIOR_MAP.get(bid_a, {}).get("label", bid_a)
                label_b = BEHAVIOR_MAP.get(bid_b, {}).get("label", bid_b)

                if r > 0:
                    insight = f"When you {label_a.lower()}, your {label_b.lower()} tends to improve too."
                else:
                    insight = f"Your {label_a.lower()} and {label_b.lower()} tend to move in opposite directions."

                correlations.append({
                    "behavior_a": bid_a,
                    "behavior_b": bid_b,
                    "r": round(r, 3),
                    "direction": "positive" if r > 0 else "negative",
                    "data_points": len(common),
                    "insight_text": insight,
                })

    correlations.sort(key=lambda c: abs(c["r"]), reverse=True)
    return correlations


def select_weekly_insight(
    correlations: List[dict],
    previously_shown: List[str],
) -> Optional[dict]:
    """Pick at most 1 new correlation insight for this week's digest.

    `previously_shown` is a list of "bidA|bidB" keys.
    """
    for corr in correlations:
        key = f"{corr['behavior_a']}|{corr['behavior_b']}"
        key_rev = f"{corr['behavior_b']}|{corr['behavior_a']}"
        if key not in previously_shown and key_rev not in previously_shown:
            return corr
    return None


# ---------------------------------------------------------------------------
# Heart Note Pattern Detection
# ---------------------------------------------------------------------------

MIN_PATTERN_DATA_DAYS = 14

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def detect_heart_note_temporal_patterns(
    daily_logs: List[dict],
    window_days: int = 30,
) -> List[dict]:
    """Detect temporal patterns in heart note frequency by day-of-week.

    E.g. "Your gratitude notes peak on Fridays."
    Requires 14+ days of data.
    """
    recent = daily_logs[-window_days:] if len(daily_logs) > window_days else daily_logs
    if len(recent) < MIN_PATTERN_DATA_DAYS:
        return []

    day_type_counts: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for log in recent:
        date_str = log.get("date", "")
        notes = log.get("heart_notes", [])
        if not date_str or not notes:
            continue
        try:
            dow = datetime.strptime(date_str, "%Y-%m-%d").weekday()
        except ValueError:
            continue
        for note in notes:
            ntype = note.get("type", "")
            if ntype:
                day_type_counts[dow][ntype] += 1

    # Aggregate per-type totals
    type_totals: Dict[str, int] = defaultdict(int)
    for dow_counts in day_type_counts.values():
        for ntype, count in dow_counts.items():
            type_totals[ntype] += count

    # Detect peaks: type on a specific day is 2x+ the average for that type
    patterns = []
    for ntype, total in type_totals.items():
        avg_per_day = total / 7.0
        if avg_per_day < 0.5:
            continue
        for dow in range(7):
            count = day_type_counts[dow].get(ntype, 0)
            if count >= 2 * avg_per_day and count >= 2:
                patterns.append({
                    "type": "temporal_peak",
                    "note_type": ntype,
                    "day_of_week": dow,
                    "day_name": _DAY_NAMES[dow],
                    "count": count,
                    "average": round(avg_per_day, 1),
                    "insight_text": f"Your {ntype} notes peak on {_DAY_NAMES[dow]}s.",
                })

    return patterns


def detect_heart_note_emotional_arcs(
    daily_logs: List[dict],
    window_days: int = 28,
) -> List[dict]:
    """Detect week-over-week shifts in heart note type distribution.

    Compares this week's type distribution to previous week's.
    Returns shifts of 15%+ as notable arcs.
    """
    recent = daily_logs[-window_days:] if len(daily_logs) > window_days else daily_logs
    if len(recent) < MIN_PATTERN_DATA_DAYS:
        return []

    recent_half = recent[-7:]
    prior_half = recent[-14:-7]

    def count_types(logs):
        counts: Dict[str, int] = defaultdict(int)
        total = 0
        for log in logs:
            for note in log.get("heart_notes", []):
                ntype = note.get("type", "")
                if ntype:
                    counts[ntype] += 1
                    total += 1
        return counts, total

    recent_counts, recent_total = count_types(recent_half)
    prior_counts, prior_total = count_types(prior_half)

    if recent_total < 3 or prior_total < 3:
        return []

    arcs = []
    all_types = set(recent_counts) | set(prior_counts)
    for ntype in all_types:
        r_pct = recent_counts.get(ntype, 0) / recent_total
        p_pct = prior_counts.get(ntype, 0) / prior_total
        shift = r_pct - p_pct
        if abs(shift) >= 0.15:
            direction = "increasing" if shift > 0 else "decreasing"
            arcs.append({
                "type": "emotional_arc",
                "note_type": ntype,
                "direction": direction,
                "shift_pct": round(shift * 100, 1),
                "insight_text": f"Your {ntype} notes have been {direction} this week compared to last.",
            })

    return arcs


def detect_heart_note_score_correlation(
    daily_logs: List[dict],
    tracked_ids: List[str],
    window_days: int = 30,
) -> Optional[dict]:
    """Detect if days with heart notes correlate with higher behavioral scores.

    Returns insight like "Days with heart notes show 25% higher scores."
    """
    recent = daily_logs[-window_days:] if len(daily_logs) > window_days else daily_logs
    if len(recent) < MIN_PATTERN_DATA_DAYS:
        return None

    note_day_scores = []
    no_note_day_scores = []

    for log in recent:
        behaviors = log.get("behaviors", {})
        if not behaviors:
            continue
        cat_scores = aggregate_category_scores(behaviors, tracked_ids)
        daily_composite = sum(
            BASE_WEIGHTS.get(cat, 0) * cat_scores.get(cat, 0)
            for cat in IMAN_CATEGORIES
        )

        notes = log.get("heart_notes", [])
        if notes and len(notes) > 0:
            note_day_scores.append(daily_composite)
        else:
            no_note_day_scores.append(daily_composite)

    if len(note_day_scores) < 3 or len(no_note_day_scores) < 3:
        return None

    avg_with = sum(note_day_scores) / len(note_day_scores)
    avg_without = sum(no_note_day_scores) / len(no_note_day_scores)

    if avg_without < 0.01:
        return None

    pct_diff = ((avg_with - avg_without) / avg_without) * 100

    if abs(pct_diff) < 10:
        return None

    if pct_diff > 0:
        insight = f"Days when you write heart notes show {round(pct_diff)}% higher behavioral scores."
    else:
        insight = "Your heart notes tend to come on quieter days — that is its own form of worship."

    return {
        "type": "score_correlation",
        "pct_difference": round(pct_diff, 1),
        "note_days_count": len(note_day_scores),
        "no_note_days_count": len(no_note_day_scores),
        "insight_text": insight,
    }


def compute_heart_note_patterns(
    daily_logs: List[dict],
    tracked_ids: List[str],
    window_days: int = 30,
) -> dict:
    """Compute all heart note patterns. Returns dict with temporal, arcs, correlation."""
    temporal = detect_heart_note_temporal_patterns(daily_logs, window_days)
    arcs = detect_heart_note_emotional_arcs(daily_logs, window_days)
    correlation = detect_heart_note_score_correlation(daily_logs, tracked_ids, window_days)

    return {
        "temporal_patterns": temporal,
        "emotional_arcs": arcs,
        "score_correlation": correlation,
        "has_patterns": bool(temporal or arcs or correlation),
        "min_days_needed": MIN_PATTERN_DATA_DAYS,
    }


def compute_category_pillars(
    scores_7d: List[float],
    scores_14d: List[float],
    baseline_median: float,
    baseline_mad: float,
) -> dict:
    """Compute the three pillars for a single category.

    Returns {performance, consistency, trajectory, composite}.
    """
    # Pillar 1: Relative Performance (7-day window vs baseline)
    if scores_7d:
        mean_7d = sum(scores_7d) / len(scores_7d)
        p_raw = (mean_7d - baseline_median) / max(baseline_mad, 0.10)
        p_clamped = max(min(p_raw, 2.0), -2.0)
        performance = p_clamped / 2.0  # Scale to [-1, 1]
    else:
        performance = 0.0

    # Pillar 2: Consistency (7-day window)
    if len(scores_7d) >= 2:
        mean_w = sum(scores_7d) / len(scores_7d)
        std_w = statistics.stdev(scores_7d)
        if mean_w < 0.05:
            # Don't reward "consistency" of doing nothing
            consistency = 0.0
        else:
            consistency = 1.0 - (std_w / max(mean_w, 0.10))
            consistency = max(min(consistency, 1.0), 0.0)
    else:
        consistency = 0.0

    # Pillar 3: Trajectory (14-day window — directional momentum)
    if len(scores_14d) >= 3:
        days = list(range(len(scores_14d)))
        trajectory = _pearson_r(days, scores_14d)
    else:
        trajectory = 0.0

    # Category composite
    composite = (
        PILLAR_ALPHA * performance +
        PILLAR_BETA * consistency +
        PILLAR_GAMMA * trajectory
    )

    return {
        "performance": round(performance, 3),
        "consistency": round(consistency, 3),
        "trajectory": round(trajectory, 3),
        "composite": round(composite, 3),
    }


# ---------------------------------------------------------------------------
# Steps 5-7: Weighted Composite & Sigmoid
# ---------------------------------------------------------------------------

def compute_composite_index(
    category_composites: Dict[str, float],
    weights: Optional[Dict[str, float]] = None,
) -> float:
    """Weighted sum of category composites.

    Uses base weights if none provided.
    """
    w = weights or BASE_WEIGHTS
    total = sum(
        w.get(cat, 0) * category_composites.get(cat, 0)
        for cat in IMAN_CATEGORIES
    )
    return total


def sigmoid_normalize(raw_index: float) -> float:
    """Sigmoid normalization to [0, 100]. Internal only — never shown to user."""
    return 100.0 / (1.0 + math.exp(-3.0 * raw_index))


# ---------------------------------------------------------------------------
# Step 8: Trajectory State Display
# ---------------------------------------------------------------------------

def _linear_regression_slope(values: List[float]) -> float:
    """Slope of least-squares linear regression on values indexed 0..N-1."""
    n = len(values)
    if n < 2:
        return 0.0

    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n

    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if abs(denominator) < 1e-10:
        return 0.0
    return numerator / denominator


def compute_trajectory_state(daily_composites_14d: List[float]) -> dict:
    """Compute trajectory state and volatility from 14 days of composite scores.

    Returns display-ready dict with state, volatility, arrow, color.
    """
    if len(daily_composites_14d) < 3:
        return {
            "current_state": "calibrating",
            "volatility_state": "stable",
            "composite_display": "Calibrating",
            "trend_slope": 0.0,
            "volatility_cv": 0.0,
        }

    # Trajectory state from slope
    slope = _linear_regression_slope(daily_composites_14d)

    if slope > 0.3:
        state = "ascending"
        display_state = "Ascending"
        color = "#2D8A6E"
    elif slope > 0.05:
        state = "gently_rising"
        display_state = "Gently Rising"
        color = "#4AA88A"
    elif slope >= -0.1:
        state = "steady"
        display_state = "Steady"
        color = "#B8860B"
    else:
        state = "recalibrating"
        display_state = "Recalibrating"
        color = "#8B7355"

    # Volatility state from coefficient of variation
    mean_val = sum(daily_composites_14d) / len(daily_composites_14d)
    if abs(mean_val) < 1e-10:
        cv = 0.0
    else:
        std_val = statistics.stdev(daily_composites_14d) if len(daily_composites_14d) >= 2 else 0.0
        cv = std_val / abs(mean_val)

    if cv < 0.08:
        vol = "stable"
    elif cv <= 0.20:
        vol = "dynamic"
    else:
        vol = "turbulent"

    vol_display = vol.capitalize()
    composite_display = f"{display_state} & {vol_display}"

    return {
        "current_state": state,
        "volatility_state": vol,
        "composite_display": composite_display,
        "trend_slope": round(slope, 4),
        "volatility_cv": round(cv, 4),
        "color": color,
    }


# ---------------------------------------------------------------------------
# Full Pipeline: recompute_trajectory
# ---------------------------------------------------------------------------

def recompute_trajectory(
    daily_logs: List[dict],
    config: dict,
    current_baselines: Optional[dict] = None,
) -> Tuple[dict, Optional[dict]]:
    """Full Iman Index pipeline: logs → category scores → pillars → trajectory.

    Called synchronously on each POST /iman/log.

    Args:
        daily_logs: List of daily log documents sorted by date ascending.
                    Each has {date, behaviors: {id: {value, ...}}}
        config: The user's iman_config/settings document.
        current_baselines: Existing baselines (None if not yet established).

    Returns:
        (trajectory_doc, new_baselines_or_none)
        trajectory_doc: Full trajectory document for Firestore.
        new_baselines_or_none: New baselines if computed/recalibrated, else None.
    """
    tracked_ids = get_tracked_behavior_ids(config)
    now = datetime.now(timezone.utc).isoformat()
    days_logged = len(daily_logs)

    # Step 2: Aggregate category scores for each day
    all_category_scores = []
    for log in daily_logs:
        behaviors = log.get("behaviors", {})
        cat_scores = aggregate_category_scores(behaviors, tracked_ids)
        all_category_scores.append(cat_scores)

    # Step 3: Compute baselines if needed
    new_baselines = None
    baseline_established = config.get("baseline_established", False)

    if not baseline_established and days_logged >= CALIBRATION_DAYS:
        # Initial baseline from calibration period
        new_baselines = compute_baselines(all_category_scores[:CALIBRATION_DAYS])
        baseline_established = True
    elif baseline_established and current_baselines:
        # Check if recalibration is due (every 30 days)
        last_recal = current_baselines.get("last_recalibration", "")
        if last_recal:
            try:
                last_dt = datetime.fromisoformat(last_recal.replace("Z", "+00:00"))
                days_since = (datetime.now(timezone.utc) - last_dt).days
                if days_since >= RECALIBRATION_INTERVAL and days_logged >= RECALIBRATION_INTERVAL:
                    recent_scores = all_category_scores[-RECALIBRATION_INTERVAL:]
                    new_baselines = compute_baselines(recent_scores, current_baselines)
            except (ValueError, TypeError):
                pass

    # Use new baselines if computed, otherwise use existing
    baselines = new_baselines or current_baselines or {}

    # If no baselines yet (still calibrating), return calibrating state
    if not baseline_established:
        days_remaining = max(CALIBRATION_DAYS - days_logged, 0)
        trajectory_doc = {
            "current_state": "calibrating",
            "volatility_state": "stable",
            "composite_display": "Calibrating",
            "trend_slope": 0.0,
            "volatility_cv": 0.0,
            "days_logged": days_logged,
            "calibration_days_remaining": days_remaining,
            "baseline_established": False,
            "category_scores": {},
            "daily_scores": [],
            "growth_edges": [],
            "updated_at": now,
        }
        return trajectory_doc, new_baselines

    # Steps 4-5: Compute three pillars per category
    category_results = {}
    for cat_id in IMAN_CATEGORIES:
        cat_values_all = [d.get(cat_id, 0.0) for d in all_category_scores]

        # 7-day and 14-day windows
        scores_7d = cat_values_all[-7:] if len(cat_values_all) >= 7 else cat_values_all
        scores_14d = cat_values_all[-14:] if len(cat_values_all) >= 14 else cat_values_all

        bl = baselines.get(cat_id, {})
        bl_median = bl.get("median", 0.5)
        bl_mad = bl.get("mad", 0.1)

        pillars = compute_category_pillars(scores_7d, scores_14d, bl_median, bl_mad)
        category_results[cat_id] = pillars

    # Step 6-7: Composite index per day (for trajectory computation)
    composites_per_day = []
    for day_scores in all_category_scores:
        # Simple daily composite using base weights
        daily_composite = sum(
            BASE_WEIGHTS.get(cat, 0) * day_scores.get(cat, 0)
            for cat in IMAN_CATEGORIES
        )
        composites_per_day.append(daily_composite)

    # Normalized daily scores for sparkline
    daily_scores_output = []
    for i, log in enumerate(daily_logs):
        if i < len(composites_per_day):
            daily_scores_output.append({
                "date": log.get("date", ""),
                "composite": round(composites_per_day[i], 4),
            })

    # Keep last 90 days for storage
    daily_scores_output = daily_scores_output[-90:]

    # Step 8: Trajectory state from last 14 days of composites
    composites_14d = composites_per_day[-14:] if len(composites_per_day) >= 3 else composites_per_day
    trajectory_state = compute_trajectory_state(composites_14d)

    # Growth edges: categories with lowest consistency
    edges = sorted(
        category_results.items(),
        key=lambda x: x[1]["consistency"],
    )
    growth_edges = [cat_id for cat_id, _ in edges[:2]]

    trajectory_doc = {
        **trajectory_state,
        "days_logged": days_logged,
        "baseline_established": True,
        "calibration_days_remaining": 0,
        "category_scores": category_results,
        "daily_scores": daily_scores_output,
        "active_weights": dict(BASE_WEIGHTS),
        "growth_edges": growth_edges,
        "updated_at": now,
    }

    return trajectory_doc, new_baselines


# ---------------------------------------------------------------------------
# Safeguards
# ---------------------------------------------------------------------------

MAX_TRACKED_BEHAVIORS = 15


def check_behavior_cap(tracked_ids: List[str]) -> Tuple[bool, str]:
    """Reject if user tries to track more than 15 behaviors."""
    if len(tracked_ids) > MAX_TRACKED_BEHAVIORS:
        return False, f"Maximum {MAX_TRACKED_BEHAVIORS} tracked behaviors allowed. You have {len(tracked_ids)}."
    return True, ""


def should_show_anti_riya_reminder() -> bool:
    """Probabilistic: show 'a mirror, not a measure' reminder ~10% of sessions."""
    import random
    return random.random() < 0.10


_COMFORT_VERSES = [
    {"surah": 94, "verse": 5, "text": "Indeed, with hardship comes ease."},
    {"surah": 39, "verse": 53, "text": "Do not despair of the mercy of Allah."},
    {"surah": 2, "verse": 286, "text": "Allah does not burden a soul beyond that it can bear."},
    {"surah": 65, "verse": 7, "text": "Allah will bring about, after hardship, ease."},
]


def get_recalibrating_comfort(days_recalibrating: int) -> Optional[dict]:
    """If recalibrating for 14+ days, return comfort verse + hide trajectory flag."""
    if days_recalibrating < 14:
        return None
    import random
    verse = random.choice(_COMFORT_VERSES)
    return {
        "hide_trajectory": True,
        "comfort_verse": verse,
        "message": "Your journey is between you and Allah. Every return is honored.",
    }


def get_welcome_back_message(days_absent: int) -> Optional[str]:
    """Warm welcome-back message for users returning after a gap. No guilt."""
    if days_absent < 2:
        return None
    if days_absent <= 7:
        return "Welcome back. Every day is a new beginning."
    if days_absent <= 30:
        return "The door is always open. Welcome back."
    return "Alhamdulillah, you are here. That is what matters."


# ---------------------------------------------------------------------------
# Strain/Recovery Engine
# ---------------------------------------------------------------------------

_QURAN_BEHAVIOR_IDS = {"quran_minutes", "tadabbur_session", "quran_memorization"}


def compute_daily_strain(
    behaviors: Dict[str, Any],
    tracked_ids: List[str],
) -> float:
    """Compute daily strain from attempted behaviors.

    Each behavior contributes strain proportional to its attempt weight
    and difficulty factor. Normalized to [0, 1].
    """
    if not behaviors or not tracked_ids:
        return 0.0

    strain = 0.0
    max_possible = 0.0

    for bid in tracked_ids:
        bdef = BEHAVIOR_MAP.get(bid)
        if not bdef:
            continue
        input_type = bdef.get("input_type", "binary")
        difficulty = STRAIN_DIFFICULTY.get(input_type, 1.0)
        max_possible += difficulty

        raw = behaviors.get(bid)
        if raw is None:
            continue

        val = raw.get("value", raw) if isinstance(raw, dict) else raw

        # Compute attempt weight based on input type
        if input_type == "binary":
            attempt_weight = 1.0 if val else 0.0
        elif input_type == "scale_5":
            attempt_weight = min(float(val) / 5.0, 1.0) if val else 0.0
        elif input_type in ("minutes", "hours", "count", "count_inv"):
            attempt_weight = min(float(val) / max(1.0, float(val) + 1.0), 1.0) if val else 0.0
        else:
            attempt_weight = 1.0 if val else 0.0

        strain += attempt_weight * difficulty

    if max_possible <= 0:
        return 0.0
    return min(strain / max_possible, 1.0)


def compute_daily_recovery(log: dict) -> float:
    """Compute daily recovery score from restorative practices.

    Components: heart_notes (0.25), quran (0.25), dhikr (0.20),
    sleep quality (0.15), reflection notes (0.15). Returns [0, 1].
    """
    recovery = 0.0
    behaviors = log.get("behaviors", {})
    heart_notes = log.get("heart_notes", [])

    # Heart notes presence (0.25)
    if len(heart_notes) > 0:
        recovery += 0.25

    # Quran engagement (0.25)
    for qid in _QURAN_BEHAVIOR_IDS:
        raw = behaviors.get(qid)
        if raw is not None:
            val = raw.get("value", raw) if isinstance(raw, dict) else raw
            if val and float(val) > 0:
                recovery += 0.25
                break

    # Dhikr (0.20)
    dhikr_raw = behaviors.get("dhikr_minutes")
    if dhikr_raw is not None:
        val = dhikr_raw.get("value", dhikr_raw) if isinstance(dhikr_raw, dict) else dhikr_raw
        if val and float(val) > 0:
            recovery += 0.20

    # Sleep quality — Gaussian centered at 7.5h (0.15)
    sleep_raw = behaviors.get("sleep_hours")
    if sleep_raw is not None:
        val = sleep_raw.get("value", sleep_raw) if isinstance(sleep_raw, dict) else sleep_raw
        if val is not None:
            hours = float(val)
            # Gaussian: peak at 7.5, sigma=1.5
            sleep_quality = math.exp(-0.5 * ((hours - 7.5) / 1.5) ** 2)
            recovery += 0.15 * sleep_quality

    # Reflection notes (0.15)
    for note in heart_notes:
        ntype = note.get("type", "") if isinstance(note, dict) else ""
        if ntype in ("reflection", "quran_insight"):
            recovery += 0.15
            break

    return min(recovery, 1.0)


_SR_STATUS_MESSAGES = {
    "restorative": "A season of restoration. Your spirit is being nourished.",
    "balanced": "Effort and rest in harmony. This is the Prophetic balance.",
    "high_strain": (
        "You are striving hard. Consider: the Prophet \u2e0e said, "
        "'Take on only what you can do.'"
    ),
    "burnout_risk": (
        "Your body has a right over you. "
        "Consider easing one practice this week."
    ),
}


def compute_strain_recovery(
    daily_logs: List[dict],
    tracked_ids: List[str],
    window_days: int = 7,
) -> dict:
    """Compute strain/recovery ratio over a sliding window.

    Returns display-ready dict with ratio, status, percentages, and message.
    """
    recent = daily_logs[-window_days:] if len(daily_logs) > window_days else daily_logs

    if not recent:
        return {
            "mean_strain": 0.0,
            "mean_recovery": 0.0,
            "sr_ratio": 0.0,
            "sr_status": "balanced",
            "strain_pct": 0,
            "recovery_pct": 0,
            "status_message": _SR_STATUS_MESSAGES["balanced"],
        }

    strains = [compute_daily_strain(log.get("behaviors", {}), tracked_ids) for log in recent]
    recoveries = [compute_daily_recovery(log) for log in recent]

    mean_strain = sum(strains) / len(strains)
    mean_recovery = sum(recoveries) / len(recoveries)
    sr_ratio = mean_strain / max(mean_recovery, 0.1)

    if sr_ratio < SR_RESTORATIVE_UPPER:
        sr_status = "restorative"
    elif sr_ratio <= SR_BALANCED_UPPER:
        sr_status = "balanced"
    elif sr_ratio <= SR_HIGH_STRAIN_UPPER:
        sr_status = "high_strain"
    else:
        sr_status = "burnout_risk"

    return {
        "mean_strain": round(mean_strain, 3),
        "mean_recovery": round(mean_recovery, 3),
        "sr_ratio": round(sr_ratio, 3),
        "sr_status": sr_status,
        "strain_pct": round(mean_strain * 100),
        "recovery_pct": round(mean_recovery * 100),
        "status_message": _SR_STATUS_MESSAGES[sr_status],
    }


def compute_strain_trend(
    daily_logs: List[dict],
    tracked_ids: List[str],
) -> dict:
    """3-day strain trend extrapolation for burnout prediction."""
    if len(daily_logs) < 3:
        return {"trend": "insufficient_data", "direction": None, "message": None}

    recent_3 = daily_logs[-3:]
    strains = [compute_daily_strain(log.get("behaviors", {}), tracked_ids) for log in recent_3]

    xs = [0, 1, 2]
    r = _pearson_r(xs, strains)
    slope = (strains[-1] - strains[0]) / 2

    if r > 0.5 and slope > 0.15:
        return {
            "trend": "rising",
            "direction": "up",
            "message": "Your effort has been increasing steadily. Remember: the body has a right over you.",
        }
    elif r < -0.5 and slope < -0.15:
        return {
            "trend": "easing",
            "direction": "down",
            "message": None,
        }
    return {"trend": "stable", "direction": None, "message": None}


# ---------------------------------------------------------------------------
# Advanced Safeguards
# ---------------------------------------------------------------------------

def detect_scrupulosity_signals(daily_logs: List[dict]) -> dict:
    """Detect scrupulosity (waswasah) signals from recent logging patterns.

    Signals: (a) all heart notes are tawbah for 7+ days,
    (b) avoided_sins always 1/5 for 7+ days.
    Active if 2+ signals present.
    """
    recent = daily_logs[-SCRUPULOSITY_TAWBAH_STREAK_DAYS:]
    if len(recent) < SCRUPULOSITY_TAWBAH_STREAK_DAYS:
        return {"active": False, "signals": [], "message": None}

    signals = []

    # Signal 1: All heart notes are tawbah
    all_tawbah = True
    any_notes = False
    for log in recent:
        notes = log.get("heart_notes", [])
        for note in notes:
            any_notes = True
            ntype = note.get("type", "") if isinstance(note, dict) else ""
            if ntype != "tawbah":
                all_tawbah = False
                break
        if not all_tawbah:
            break
    if all_tawbah and any_notes:
        signals.append("all_tawbah_notes")

    # Signal 2: avoided_sins always 1 (lowest) for all recent days
    all_low_sins = True
    any_sins_data = False
    for log in recent:
        behaviors = log.get("behaviors", {})
        raw = behaviors.get("avoided_sins")
        if raw is not None:
            any_sins_data = True
            val = raw.get("value", raw) if isinstance(raw, dict) else raw
            if val is not None and float(val) > 1:
                all_low_sins = False
                break
    if all_low_sins and any_sins_data:
        signals.append("always_low_self_assessment")

    active = len(signals) >= 2
    message = (
        "Gentleness is itself worship. The Prophet \u2e0e said: "
        "'Allah is gentle and loves gentleness in all things.' "
        "You are doing enough."
    ) if active else None

    return {"active": active, "signals": signals, "message": message}


def detect_burnout_state(sr_data: dict) -> dict:
    """Detect burnout state from strain/recovery data.

    Triggers when SR status is burnout_risk.
    """
    if sr_data.get("sr_status") == "burnout_risk":
        return {
            "active": True,
            "message": (
                "Your body has a right over you, your eyes have a right over you. "
                "Consider removing one tracked behavior this week."
            ),
            "suggest_remove_behavior": True,
        }
    return {"active": False, "message": None, "suggest_remove_behavior": False}


def should_show_humility_reset(uid: str, trajectory_state: str) -> dict:
    """Deterministic monthly humility reset.

    Uses hash(uid + date) for consistency within a day. Only triggers
    on ascending/gently_rising states to avoid piling on during hard times.
    """
    if trajectory_state not in ("ascending", "gently_rising"):
        return {"active": False}

    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    h = hash(uid + date_str + "humility")
    if h % HUMILITY_RESET_FRACTION != 0:
        return {"active": False}

    return {
        "active": True,
        "message": "Allah Knows Best",
        "hadith": (
            "None of you will enter Paradise by their deeds alone. "
            "\u2014 Prophet Muhammad \u2e0e (Bukhari)"
        ),
        "instruction": "The trajectory is paused today. Just be with Allah.",
    }


def detect_emergency_override(daily_logs: List[dict]) -> dict:
    """Detect emergency state: 7+ consecutive days of grieving/spiritually_dry.

    When active, suggests disabling Iman Index and shows hope verse.
    """
    recent = daily_logs[-EMERGENCY_CONSECUTIVE_DAYS:]
    if len(recent) < EMERGENCY_CONSECUTIVE_DAYS:
        return {"active": False}

    distress_states = {"grieving", "spiritually_dry"}
    all_distressed = all(
        log.get("heart_state") in distress_states
        for log in recent
    )

    if not all_distressed:
        return {"active": False}

    return {
        "active": True,
        "consecutive_days": len(recent),
        "verse": {
            "surah": 93,
            "verse": 3,
            "text": "Your Lord has not forsaken you, nor has He become displeased.",
        },
        "message": (
            "Would you like to pause tracking and just be? "
            "This tool should serve you, not burden you."
        ),
    }


def get_reduced_journal_config(days_recalibrating: int) -> Optional[dict]:
    """Offer simplified 3-behavior journal after 14+ days recalibrating."""
    if days_recalibrating < REDUCED_JOURNAL_RECAL_DAYS:
        return None
    return {
        "active": True,
        "suggested_behaviors": REDUCED_JOURNAL_BEHAVIORS,
        "message": (
            "Let's simplify. When the heart is heavy, "
            "do the minimum with maximum presence."
        ),
    }


def compute_safeguard_status(
    daily_logs: List[dict],
    trajectory: dict,
    sr_data: dict,
    uid: str,
    days_recalibrating: int = 0,
) -> dict:
    """Orchestrate all safeguard checks. Returns unified status dict."""
    scrupulosity = detect_scrupulosity_signals(daily_logs)
    burnout = detect_burnout_state(sr_data)
    humility = should_show_humility_reset(uid, trajectory.get("current_state", "calibrating"))
    emergency = detect_emergency_override(daily_logs)
    reduced = get_reduced_journal_config(days_recalibrating)

    any_active = (
        scrupulosity["active"]
        or burnout["active"]
        or humility.get("active", False)
        or emergency["active"]
        or (reduced is not None and reduced.get("active", False))
    )

    return {
        "scrupulosity": scrupulosity,
        "burnout": burnout,
        "humility_reset": humility,
        "emergency_override": emergency,
        "reduced_journal": reduced,
        "any_active": any_active,
    }


# ---------------------------------------------------------------------------
# Struggle Progress
# ---------------------------------------------------------------------------

STRUGGLE_PHASE_WEEKS = 4  # Each struggle has 4 phases, one per week


def compute_struggle_progress(
    struggle_id: str,
    declared_at: str,
    daily_logs: List[dict],
    struggle_config: dict,
) -> dict:
    """
    Compute progress for an active struggle.

    Args:
        struggle_id: ID from STRUGGLE_CATALOG
        declared_at: ISO timestamp when the struggle was declared
        daily_logs: Recent daily logs (last 30 days)
        struggle_config: The struggle dict from STRUGGLE_CATALOG

    Returns:
        Dict with current_phase, phase_title, weeks_active,
        linked_behavior_trends, phase_progress_pct
    """
    from datetime import datetime

    now = datetime.utcnow()
    try:
        start = datetime.fromisoformat(declared_at.replace("Z", "+00:00")).replace(tzinfo=None)
    except (ValueError, AttributeError):
        start = now

    days_active = max(0, (now - start).days)
    weeks_active = days_active // 7

    # Map to phase 0-3 (cap at 3)
    current_phase = min(weeks_active, STRUGGLE_PHASE_WEEKS - 1)
    phases = struggle_config.get("phases", [])
    phase_title = phases[current_phase] if current_phase < len(phases) else ""

    # Progress within current phase (0-100%)
    days_in_phase = days_active - (current_phase * 7)
    phase_progress_pct = min(100, round((days_in_phase / 7) * 100))

    # Linked behavior trends: compute 14-day slope for each linked behavior
    linked_ids = struggle_config.get("linked_behaviors", [])
    linked_behavior_trends = {}

    if daily_logs and linked_ids:
        # Build time series per linked behavior from last 14 days
        recent = daily_logs[-14:] if len(daily_logs) > 14 else daily_logs
        for bid in linked_ids:
            values = []
            for log in recent:
                behaviors = log.get("behaviors", {})
                if bid in behaviors:
                    val = behaviors[bid]
                    if isinstance(val, (int, float)):
                        values.append(float(val))
                    elif isinstance(val, bool):
                        values.append(1.0 if val else 0.0)

            if len(values) >= 3:
                xs = list(range(len(values)))
                r = _pearson_r(xs, values)
                if r > 0.2:
                    linked_behavior_trends[bid] = "improving"
                elif r < -0.2:
                    linked_behavior_trends[bid] = "declining"
                else:
                    linked_behavior_trends[bid] = "stable"
            else:
                linked_behavior_trends[bid] = "insufficient_data"

    # Milestone detection: phase transition
    milestone = None
    if current_phase > 0 and days_in_phase <= 1:
        milestone = {
            "just_transitioned": True,
            "phase_completed": current_phase,
            "phase_label": phases[current_phase] if current_phase < len(phases) else "",
            "previous_phase_label": phases[current_phase - 1] if (current_phase - 1) < len(phases) else "",
        }

    return {
        "current_phase": current_phase,
        "phase_title": phase_title,
        "weeks_active": weeks_active,
        "days_active": days_active,
        "phase_progress_pct": phase_progress_pct,
        "linked_behavior_trends": linked_behavior_trends,
        "milestone": milestone,
    }


# ---------------------------------------------------------------------------
# Daily Insight — Context & Prompt Builder
# ---------------------------------------------------------------------------

def prepare_daily_insight_context(
    today_log: dict,
    recent_logs: List[dict],
    trajectory: dict,
    config: dict,
    active_struggles: List[dict],
) -> dict:
    """Prepare context for the Gemini daily insight prompt."""
    tracked_ids = get_tracked_behavior_ids(config)

    # Today's behavior summary
    behaviors = today_log.get("behaviors", {})
    behavior_summary_parts = []
    for bid in tracked_ids:
        raw = behaviors.get(bid)
        if raw is not None:
            val = raw.get("value", raw) if isinstance(raw, dict) else raw
            label = BEHAVIOR_MAP.get(bid, {}).get("label", bid)
            behavior_summary_parts.append(f"{label}: {val}")
    behavior_summary = ", ".join(behavior_summary_parts) if behavior_summary_parts else "No behaviors logged"

    # Consistency summary from recent logs
    days_with_logs = len(recent_logs)
    consistency_summary = f"{days_with_logs}/7 days logged in the past week"

    # Strain status
    sr = compute_strain_recovery(recent_logs, tracked_ids)
    strain_status = sr.get("sr_status", "balanced")

    # Struggle summary
    struggle_parts = []
    for s in active_struggles:
        progress = s.get("progress", {})
        struggle_parts.append(f"{s.get('label', '')} (week {progress.get('weeks_active', 0) + 1})")
    struggle_summary = ", ".join(struggle_parts) if struggle_parts else "None"

    return {
        "date": today_log.get("date", ""),
        "behavior_summary": behavior_summary,
        "heart_state": today_log.get("heart_state"),
        "heart_note_count": len(today_log.get("heart_notes", [])),
        "days_total": trajectory.get("days_logged", 0),
        "consistency_summary": consistency_summary,
        "strain_status": strain_status,
        "struggle_summary": struggle_summary,
    }


def build_daily_insight_prompt(context: dict, persona_name: str = "practicing_muslim") -> str:
    """Build the Gemini prompt for a daily spiritual insight."""
    tone = _PERSONA_TONE.get(persona_name, _PERSONA_TONE["practicing_muslim"])

    prompt = f"""You are a gentle spiritual companion reflecting on a Muslim's day of practice.

TONE: {tone}

CRITICAL RULES:
- NEVER show raw numbers, scores, percentages, or indices.
- NEVER say "you should" or "you must". Use "you might consider", "perhaps", "one beautiful practice is..."
- Stay under 120 words total across all fields.
- Write with warmth and mercy.
- Be SPECIFIC to their actual data — reference actual behaviors, not generic advice.

TODAY'S LOG ({context['date']}):
Behaviors logged: {context['behavior_summary']}
Heart state: {context['heart_state'] or 'Not recorded'}
Heart notes: {context['heart_note_count']} written
Streak: Day {context['days_total']} on their journey

RECENT CONTEXT (last 7 days):
Consistency: {context['consistency_summary']}
Strain level: {context['strain_status']}
Active struggles: {context['struggle_summary']}

Respond in VALID JSON with exactly these 4 keys:
{{
  "observation": "A 1-sentence specific observation about today's log. Be concrete.",
  "correlation": "If you notice a pattern with recent days, share it naturally. Otherwise null.",
  "encouragement": "A 1-sentence genuine encouragement rooted in what they actually did.",
  "strain_note": "If strain is high or rising, a gentle 1-sentence reminder. Otherwise null."
}}"""
    return prompt


# ---------------------------------------------------------------------------
# Weekly Digest — Context & Prompt Builder
# ---------------------------------------------------------------------------

def prepare_digest_context(
    daily_logs: List[dict],
    trajectory: dict,
    config: dict,
    heart_notes: List[dict],
    active_struggles: List[dict],
    week_start: str,
    week_end: str,
) -> dict:
    """
    Prepare all context needed for the Gemini weekly digest prompt.

    Args:
        daily_logs: All daily logs (ideally 90 days, for correlation window)
        trajectory: Current trajectory doc
        config: User's iman config
        heart_notes: Decrypted heart notes from the week
        active_struggles: Active struggle dicts with progress
        week_start: ISO date string (YYYY-MM-DD) for week start
        week_end: ISO date string (YYYY-MM-DD) for week end

    Returns:
        Context dict with all fields for prompt building.
    """
    from collections import Counter

    # Filter logs to the target week
    week_logs = [
        log for log in daily_logs
        if week_start <= log.get("date", "") <= week_end
    ]
    days_logged_this_week = len(week_logs)

    # Aggregate category scores for the week
    tracked_ids = get_tracked_behavior_ids(config)
    weekly_category_totals = {}
    weekly_behavior_summary = {}

    for log in week_logs:
        behaviors = log.get("behaviors", {})
        for bid, val in behaviors.items():
            if bid not in weekly_behavior_summary:
                weekly_behavior_summary[bid] = {"values": [], "days_logged": 0}
            weekly_behavior_summary[bid]["values"].append(val)
            weekly_behavior_summary[bid]["days_logged"] += 1

    # Compute average and trend per behavior
    for bid, info in weekly_behavior_summary.items():
        vals = info["values"]
        numeric = [float(v) for v in vals if isinstance(v, (int, float))]
        if numeric:
            info["average"] = round(sum(numeric) / len(numeric), 2)
        else:
            bool_vals = [1.0 if v else 0.0 for v in vals if isinstance(v, bool)]
            info["average"] = round(sum(bool_vals) / len(bool_vals), 2) if bool_vals else 0

        # Simple trend: compare first half vs second half
        if len(numeric) >= 4:
            mid = len(numeric) // 2
            first_half = sum(numeric[:mid]) / mid
            second_half = sum(numeric[mid:]) / (len(numeric) - mid)
            if second_half > first_half * 1.1:
                info["trend"] = "improving"
            elif second_half < first_half * 0.9:
                info["trend"] = "declining"
            else:
                info["trend"] = "stable"
        else:
            info["trend"] = "insufficient_data"

    # Heart state summary
    heart_state_counts = Counter()
    for log in week_logs:
        hs = log.get("heart_state")
        if hs:
            heart_state_counts[hs] += 1

    # Heart note type counts
    heart_note_types = Counter()
    for note in heart_notes:
        heart_note_types[note.get("type", "other")] += 1

    # Run correlations on full 90-day window
    correlations = compute_behavior_correlations(daily_logs, tracked_ids, window_days=90)

    # Struggle summaries
    struggle_summaries = []
    for s in active_struggles:
        progress = s.get("progress", {})
        struggle_summaries.append({
            "label": s.get("label", ""),
            "weeks_active": progress.get("weeks_active", 0),
            "phase_title": progress.get("phase_title", ""),
            "linked_trends": progress.get("linked_behavior_trends", {}),
        })

    return {
        "week_start": week_start,
        "week_end": week_end,
        "days_logged_this_week": days_logged_this_week,
        "trajectory_state": trajectory.get("current_state", "calibrating"),
        "trajectory_display": trajectory.get("composite_display", ""),
        "volatility": trajectory.get("volatility_state", ""),
        "days_total": trajectory.get("days_logged", 0),
        "behavior_summary": {
            bid: {
                "label": BEHAVIOR_MAP.get(bid, {}).get("label", bid),
                "average": info["average"],
                "days_logged": info["days_logged"],
                "trend": info["trend"],
            }
            for bid, info in weekly_behavior_summary.items()
        },
        "heart_states": dict(heart_state_counts),
        "heart_note_count": len(heart_notes),
        "heart_note_types": dict(heart_note_types),
        "correlations": [
            {
                "pair": f"{c['behavior_a']}|{c['behavior_b']}",
                "r": c["r"],
                "insight": c["insight_text"],
            }
            for c in correlations[:5]
        ],
        "struggles": struggle_summaries,
        "growth_edges": trajectory.get("growth_edges", []),
        "heart_note_patterns": compute_heart_note_patterns(daily_logs, tracked_ids, window_days=90),
    }


# Persona tone mapping for digest prompts
_PERSONA_TONE = {
    "new_revert": "Speak gently and simply, as to someone new to the path. Avoid jargon.",
    "curious_explorer": "Be warm and inviting, like a thoughtful companion on a journey of discovery.",
    "practicing_muslim": "Be balanced and respectful, speaking as peer to peer.",
    "student": "Be precise and educational, connecting observations to scholarly tradition.",
    "advanced_learner": "Be deep and nuanced, drawing from the subtleties of the spiritual sciences.",
}


def build_digest_prompt(context: dict, persona_name: str = "practicing_muslim") -> str:
    """
    Build the Gemini prompt for a weekly spiritual digest.

    Args:
        context: Output of prepare_digest_context()
        persona_name: Key from PERSONAS dict

    Returns:
        Prompt string for Gemini.
    """
    tone = _PERSONA_TONE.get(persona_name, _PERSONA_TONE["practicing_muslim"])

    # Format behavior summary
    behavior_lines = []
    for bid, info in context.get("behavior_summary", {}).items():
        behavior_lines.append(
            f"  - {info['label']}: avg={info['average']}, "
            f"logged {info['days_logged']}/{context['days_logged_this_week']} days, "
            f"trend={info['trend']}"
        )
    behavior_text = "\n".join(behavior_lines) if behavior_lines else "  No behaviors logged this week."

    # Format heart states
    heart_lines = []
    for state, count in context.get("heart_states", {}).items():
        heart_lines.append(f"  - {state}: {count} day(s)")
    heart_text = "\n".join(heart_lines) if heart_lines else "  No heart states recorded."

    # Format correlations
    corr_lines = []
    for c in context.get("correlations", []):
        corr_lines.append(f"  - {c['insight']} (r={c['r']:.2f})")
    corr_text = "\n".join(corr_lines) if corr_lines else "  Not enough data for correlations yet."

    # Format heart note patterns
    pattern_lines = []
    patterns = context.get("heart_note_patterns", {})
    for tp in patterns.get("temporal_patterns", []):
        pattern_lines.append(f"  - {tp['insight_text']}")
    for arc in patterns.get("emotional_arcs", []):
        pattern_lines.append(f"  - {arc['insight_text']}")
    corr_p = patterns.get("score_correlation")
    if corr_p:
        pattern_lines.append(f"  - {corr_p['insight_text']}")
    pattern_text = "\n".join(pattern_lines) if pattern_lines else "  Not enough data for patterns yet."

    # Format struggles
    struggle_lines = []
    for s in context.get("struggles", []):
        trends_str = ", ".join(
            f"{k}: {v}" for k, v in s.get("linked_trends", {}).items()
        )
        struggle_lines.append(
            f"  - {s['label']} (week {s['weeks_active'] + 1}): {s['phase_title']}"
            + (f" | Trends: {trends_str}" if trends_str else "")
        )
    struggle_text = "\n".join(struggle_lines) if struggle_lines else "  No active struggles."

    prompt = f"""You are a gentle spiritual companion reflecting on a Muslim's week of spiritual practice.

TONE: {tone}

CRITICAL RULES:
- NEVER show raw numbers, scores, percentages, or indices to the user.
- NEVER say "you should", "you must", or "you need to". Use "you might consider", "perhaps", "one beautiful practice is..."
- NEVER compare the user to others or to an ideal.
- Stay under 300 words total across all sections.
- End with a note of humility — you are a mirror, not a judge.
- Write in second person ("you"), with warmth and mercy.

CONTEXT FOR THIS WEEK ({context['week_start']} to {context['week_end']}):

Overall trajectory: {context['trajectory_state']} ({context['trajectory_display']})
Days logged this week: {context['days_logged_this_week']}
Total days on journey: {context['days_total']}

Behaviors this week:
{behavior_text}

Heart states this week:
{heart_text}
Heart notes written: {context['heart_note_count']} ({', '.join(f'{k}: {v}' for k, v in context.get('heart_note_types', {}).items()) or 'none'})

Behavioral correlations observed:
{corr_text}

Heart note patterns detected:
{pattern_text}

Active spiritual struggles:
{struggle_text}

Growth edges (areas with lowest consistency):
  {', '.join(context.get('growth_edges', [])) or 'None identified yet'}

Respond in VALID JSON with exactly these 7 keys:
{{
  "opening": "A 1-2 sentence warm opening acknowledging their week.",
  "weekly_story": "A 2-3 sentence narrative of what their week looked like spiritually — weave behaviors and heart states into a story, not a report.",
  "strength_noticed": "One specific strength you noticed this week. Be concrete.",
  "correlation_insight": "If correlations exist, share one insight naturally (e.g., 'It seems that on days you...'). If no correlations, share an encouraging observation.",
  "gentle_attention": "One area that might benefit from gentle attention. Frame with mercy, not criticism.",
  "verse_to_carry": {{
    "surah": 0,
    "verse": 0,
    "text": "The verse text in English",
    "why": "A sentence explaining why this verse feels relevant to their week."
  }},
  "closing": "A 1-sentence closing with humility. Remind them this is a mirror, not a measure."
}}"""

    return prompt
