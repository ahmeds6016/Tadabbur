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


def validate_heart_note(note_type: str, text: str) -> Tuple[bool, str]:
    """Validate heart note type and text (max 280 chars)."""
    if note_type not in HEART_NOTE_TYPES:
        return False, f"Invalid heart note type: {note_type}. Must be one of: {HEART_NOTE_TYPES}"
    if not text or not text.strip():
        return False, "Heart note text cannot be empty"
    if len(text) > 280:
        return False, f"Heart note too long: {len(text)} chars (max 280)"
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
