"""
Seasonal / Time-Aware Recommendation layer.
--------------------------------------------
Implements the "Seasonal / Time-Aware Recommendation System" proposal:
adds time as a context (month, season, weekday/weekend, time-of-day) on
top of the existing Apriori / FP-Growth association-rule pipeline, so
rules can be compared across time slices instead of only mined over
all-time behavior.

This module is pure logic (no st.* UI calls except caching decorators)
so it can be unit-tested and reused by:

    views/time_aware_recommendations.py   -> the Advanced page in the
                                              full Streamlit app
    time_aware_mba_app.py                 -> the standalone prototype

Reuses pipeline.py's existing, already-battle-tested transaction /
basket / Apriori helpers instead of re-implementing them, so the
time-aware rules are produced by exactly the same engine as the rest
of the project.
"""
import numpy as np
import pandas as pd
import streamlit as st

from pipeline import (
    build_transactions,
    build_basket_df,
    run_apriori_safe,
    generate_association_rules_simple,
)


# ---------------------------------------------------------------------
# SEASON DEFINITIONS
# ---------------------------------------------------------------------
# Two schemes are offered because the proposal (section 13) is explicit
# that season labels are analytical categories, not universal rules,
# and warns against assigning one region's seasons to another region's
# data without support. "Standard" fits most retail datasets (e.g. the
# UK-based UCI Online Retail data this project already uses); "Indian"
# is offered for datasets where the Indian monsoon calendar is a better
# fit. Keep this configurable rather than hard-coded.

SEASON_SCHEMES = {
    "Standard (Meteorological)": {
        12: "Winter", 1: "Winter", 2: "Winter",
        3: "Spring", 4: "Spring", 5: "Spring",
        6: "Summer", 7: "Summer", 8: "Summer",
        9: "Autumn", 10: "Autumn", 11: "Autumn",
    },
    "Indian (Monsoon-based)": {
        12: "Winter", 1: "Winter", 2: "Winter",
        3: "Summer", 4: "Summer", 5: "Summer",
        6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
        10: "Post-Monsoon", 11: "Post-Monsoon",
    },
}

# (start_hour_inclusive, end_hour_exclusive, label)
TIME_OF_DAY_BINS = [
    (0, 6, "Night (12am-6am)"),
    (6, 12, "Morning (6am-12pm)"),
    (12, 17, "Afternoon (12pm-5pm)"),
    (17, 21, "Evening (5pm-9pm)"),
    (21, 24, "Night (9pm-12am)"),
]

MONTH_ORDER = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def hour_to_time_of_day(hour):
    for start, end, label in TIME_OF_DAY_BINS:
        if start <= hour < end:
            return label
    return "Unknown"


# ---------------------------------------------------------------------
# TIME FEATURE ENGINEERING  (proposal section 5)
# ---------------------------------------------------------------------

@st.cache_data(show_spinner="Extracting time features...")
def add_time_features(df, date_column, season_scheme="Standard (Meteorological)"):
    """Parses date_column to datetime and adds Year, Month, MonthName,
    Quarter, DayOfWeek, IsWeekend, Hour, TimeOfDay and Season columns.

    Rows whose date fails to parse are dropped rather than crashing the
    pipeline; the number dropped is returned so the caller can warn the
    user. Returns (engineered_df, rows_dropped)."""

    out = df.copy()

    parsed = pd.to_datetime(out[date_column], errors="coerce")

    rows_dropped = int(parsed.isna().sum())

    keep_mask = parsed.notna()
    out = out.loc[keep_mask].copy()
    parsed = parsed.loc[keep_mask]

    out["Year"] = parsed.dt.year
    out["Month"] = parsed.dt.month
    out["MonthName"] = parsed.dt.month_name()
    out["Quarter"] = "Q" + parsed.dt.quarter.astype(str)
    out["DayOfWeek"] = parsed.dt.day_name()
    out["IsWeekend"] = parsed.dt.dayofweek >= 5
    out["Hour"] = parsed.dt.hour
    out["TimeOfDay"] = out["Hour"].apply(hour_to_time_of_day)

    season_map = SEASON_SCHEMES.get(
        season_scheme, SEASON_SCHEMES["Standard (Meteorological)"]
    )
    out["Season"] = out["Month"].map(season_map)

    return out, rows_dropped


def available_options(engineered_df):
    """Returns the Month / Season / Time-of-Day values actually present
    in the data, in a sensible display order, for populating filter
    dropdowns (instead of showing options with zero rows behind them)."""

    months_present = set(engineered_df["MonthName"])
    months = [m for m in MONTH_ORDER if m in months_present]

    seasons = sorted(engineered_df["Season"].dropna().unique().tolist())

    times_present = set(engineered_df["TimeOfDay"])
    times = [label for _, _, label in TIME_OF_DAY_BINS if label in times_present]

    quarters = sorted(engineered_df["Quarter"].dropna().unique().tolist())

    return months, seasons, times, quarters


def filter_by_context(engineered_df, month=None, season=None,
                       weekend=None, time_of_day=None, quarter=None):
    """Applies the selected time-context filters. Every argument is
    optional / independent, matching the proposal's filter set (month,
    season, weekday/weekend, time of day) — any combination can be
    active at once."""

    filtered = engineered_df

    if month and month != "All":
        filtered = filtered[filtered["MonthName"] == month]

    if season and season != "All":
        filtered = filtered[filtered["Season"] == season]

    if quarter and quarter != "All":
        filtered = filtered[filtered["Quarter"] == quarter]

    if weekend == "Weekend only":
        filtered = filtered[filtered["IsWeekend"]]
    elif weekend == "Weekday only":
        filtered = filtered[~filtered["IsWeekend"]]

    if time_of_day and time_of_day != "All":
        filtered = filtered[filtered["TimeOfDay"] == time_of_day]

    return filtered


# ---------------------------------------------------------------------
# TIME-SLICE RULE MINING  (proposal section 7)
# ---------------------------------------------------------------------

def mine_rules_for_slice(df, transaction_column, product_column,
                          min_support=0.02, min_confidence=0.10,
                          min_lift=1.0, max_length=2):
    """Runs the same transactions -> basket -> Apriori/FP-Growth -> rules
    pipeline the rest of the app already uses (pipeline.py), scoped to
    whatever slice of the data is passed in (a time-filtered slice, or
    the full dataset for the "overall" comparison rules).

    Returns (transactions, rules_df, used_support). rules_df is an
    empty DataFrame if the slice is too small or too sparse to clear
    the thresholds — callers should treat that as "no rules for this
    slice", not an error."""

    if df is None or df.empty:
        return [], pd.DataFrame(), min_support

    transactions = build_transactions(df, transaction_column, product_column)

    if len(transactions) < 2:
        return transactions, pd.DataFrame(), min_support

    basket_df = build_basket_df(transactions)

    try:
        frequent_itemsets, used_support = run_apriori_safe(
            basket_df, min_support=min_support, max_length=max_length
        )
    except MemoryError:
        return transactions, pd.DataFrame(), min_support

    if frequent_itemsets.empty:
        return transactions, pd.DataFrame(), used_support

    rules = generate_association_rules_simple(
        frequent_itemsets, basket_df,
        min_confidence=min_confidence, min_lift=min_lift
    )

    return transactions, rules, used_support


# ---------------------------------------------------------------------
# SEASONAL STRENGTH SCORE  (proposal section 9)
# ---------------------------------------------------------------------

def _rule_key(row):
    """Order-independent, hashable key for a rule, used to match the
    same antecedent -> consequent pair across two rule sets (a time
    slice vs. the overall / all-time rule set)."""

    return (frozenset(row["antecedents"]), frozenset(row["consequents"]))


def seasonal_strength_score(slice_rules, overall_rules):
    """For every rule found in the time slice, looks up the SAME
    antecedent -> consequent pair's confidence in the overall (all-time)
    rule set and computes:

        Seasonal Strength = slice confidence / overall confidence

    per proposal section 9's example (overall 50%, July 80% -> 1.6).
    Only pairs present in BOTH rule sets are scored, since a ratio
    against nothing is meaningless — pairs unique to the slice are
    already interesting on their own and are surfaced separately by
    the caller. Returns an empty DataFrame if either input is empty."""

    if slice_rules is None or slice_rules.empty:
        return pd.DataFrame()

    if overall_rules is None or overall_rules.empty:
        return pd.DataFrame()

    overall_lookup = {
        _rule_key(row): row["confidence"]
        for _, row in overall_rules.iterrows()
    }

    rows = []

    for _, row in slice_rules.iterrows():

        overall_confidence = overall_lookup.get(_rule_key(row))

        if not overall_confidence:
            continue

        ratio = row["confidence"] / overall_confidence

        if ratio >= 1.5:
            label = "🔥 High Seasonal Relationship"
        elif ratio >= 1.15:
            label = "🟡 Moderate Seasonal Relationship"
        else:
            label = "⚪ Low / Not Seasonal"

        rows.append({
            "antecedents": row["antecedents"],
            "consequents": row["consequents"],
            "Slice Confidence": round(row["confidence"], 3),
            "Overall Confidence": round(overall_confidence, 3),
            "Seasonal Strength": round(ratio, 2),
            "Relationship": label,
            "Slice Support": round(row["support"], 4),
            "Slice Lift": round(row["lift"], 3),
        })

    result = pd.DataFrame(rows)

    if not result.empty:
        result = (
            result
            .sort_values("Seasonal Strength", ascending=False)
            .reset_index(drop=True)
        )

    return result


# ---------------------------------------------------------------------
# TREND CHART  (proposal section 10: "monthly product demand")
# ---------------------------------------------------------------------

def monthly_demand(engineered_df, product_column=None,
                    quantity_column=None, selected_product=None):
    """Month-over-month demand series. If selected_product is given,
    the series is that single product's demand; otherwise it's total
    demand across every product. Uses quantity_column when available,
    otherwise falls back to a plain transaction/row count."""

    working = engineered_df.copy()

    working["_Period"] = (
        working["Year"].astype(str) + "-"
        + working["Month"].astype(str).str.zfill(2)
    )

    if selected_product and selected_product != "All Products" and product_column:
        working = working[working[product_column].astype(str) == selected_product]

    if quantity_column and quantity_column in working.columns:
        series = working.groupby("_Period")[quantity_column].sum()
    else:
        series = working.groupby("_Period").size()

    return series.sort_index()


# ---------------------------------------------------------------------
# TIME-BASED VALIDATION  (proposal section 12)
# ---------------------------------------------------------------------
# "Use a time-based test: recommendations for a target period should be
# generated only from information available before that period. This
# avoids future-data leakage." -> train/test are split strictly by
# date, never shuffled.

def time_based_split(engineered_df, test_fraction=0.2):
    """Sorts by date and splits the LAST test_fraction of rows (by
    time, not row count randomness) into a test set, everything before
    that cutoff into train. Returns (train_df, test_df, cutoff_year,
    cutoff_month) or (empty, empty, None, None) if there isn't enough
    data to split."""

    working = engineered_df.sort_values(["Year", "Month"])

    if len(working) < 10:
        return working.iloc[0:0], working.iloc[0:0], None, None

    cutoff_index = int(len(working) * (1 - test_fraction))
    cutoff_index = max(1, min(cutoff_index, len(working) - 1))

    cutoff_year = working["Year"].iloc[cutoff_index]
    cutoff_month = working["Month"].iloc[cutoff_index]

    cutoff_key = working["Year"] * 100 + working["Month"]
    cutoff_value = cutoff_year * 100 + cutoff_month

    train = working[cutoff_key < cutoff_value]
    test = working[cutoff_key >= cutoff_value]

    return train, test, cutoff_year, cutoff_month


def _top_k_predictions(rules_df, seen_items, k):
    """Ranks candidate consequents (score = confidence * lift) whose
    antecedent is fully contained in seen_items, and returns the top k
    product names not already in seen_items."""

    if rules_df is None or rules_df.empty:
        return []

    candidates = {}

    for _, row in rules_df.iterrows():

        if not set(row["antecedents"]).issubset(seen_items):
            continue

        score = row["confidence"] * row["lift"]

        for item in row["consequents"]:

            if item in seen_items:
                continue

            candidates[item] = max(candidates.get(item, 0.0), score)

    ranked = sorted(candidates.items(), key=lambda pair: pair[1], reverse=True)

    return [item for item, _ in ranked[:k]]


def evaluate_time_aware_vs_overall(
    train_df, test_df, transaction_column, product_column,
    context_column=None, min_support=0.02, min_confidence=0.10,
    min_lift=1.0, k=5
):
    """The proposal's evaluation (section 12): mines rules ONLY from
    train_df, then scores held-out test_df baskets by hiding all but
    the first item of each basket and checking whether the model's
    top-k recommendations recover the rest.

    Two models are compared:
      - "Existing MBA": a single rule set mined from all of train_df.
      - "Time-Aware MBA": one rule set mined per value of
        context_column within train_df (e.g. per month); a test basket
        is scored using the rule set for its OWN context value, falling
        back to the overall rules if that slice produced none.

    Returns a dict with Precision@k / Recall@k / Hit Rate@k for each
    model plus how many test baskets were evaluated. Returns None
    metrics for a model if there wasn't enough data to score it."""

    _, overall_rules, _ = mine_rules_for_slice(
        train_df, transaction_column, product_column,
        min_support=min_support, min_confidence=min_confidence,
        min_lift=min_lift, max_length=2,
    )

    context_rule_cache = {}

    if context_column:
        for value, group in train_df.groupby(context_column):
            _, group_rules, _ = mine_rules_for_slice(
                group, transaction_column, product_column,
                min_support=min_support, min_confidence=min_confidence,
                min_lift=min_lift, max_length=2,
            )
            context_rule_cache[value] = group_rules

    overall_scores = {"precision": [], "recall": [], "hit": []}
    time_aware_scores = {"precision": [], "recall": [], "hit": []}

    evaluated_baskets = 0

    for _, group in test_df.groupby(transaction_column):

        items = list(dict.fromkeys(group[product_column].dropna().astype(str)))

        if len(items) < 2:
            continue

        evaluated_baskets += 1

        seen = {items[0]}
        true_items = set(items[1:])

        overall_pred = set(_top_k_predictions(overall_rules, seen, k))
        overall_hits = overall_pred & true_items

        overall_scores["precision"].append(len(overall_hits) / k)
        overall_scores["recall"].append(len(overall_hits) / len(true_items))
        overall_scores["hit"].append(1 if overall_hits else 0)

        if context_column:

            context_value = group[context_column].iloc[0]
            slice_rules = context_rule_cache.get(context_value)

            if slice_rules is None or slice_rules.empty:
                slice_rules = overall_rules

            time_pred = set(_top_k_predictions(slice_rules, seen, k))
            time_hits = time_pred & true_items

            time_aware_scores["precision"].append(len(time_hits) / k)
            time_aware_scores["recall"].append(len(time_hits) / len(true_items))
            time_aware_scores["hit"].append(1 if time_hits else 0)

    def summarize(scores):
        if not scores["precision"]:
            return None
        return {
            "Precision@k": round(float(np.mean(scores["precision"])), 4),
            "Recall@k": round(float(np.mean(scores["recall"])), 4),
            "Hit Rate@k": round(float(np.mean(scores["hit"])), 4),
        }

    return {
        "evaluated_baskets": evaluated_baskets,
        "existing_mba": summarize(overall_scores),
        "time_aware_mba": summarize(time_aware_scores) if context_column else None,
    }
