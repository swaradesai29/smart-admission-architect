"""
engine.py
─────────────────────────────────────────────────────────────────────────────
Prediction Engine for Smart Admission Architect.

Responsibilities:
  1. Load and normalise data.json into Pandas DataFrames
  2. Compute 3-year cutoff trend (linear gradient) per college/branch/category
  3. Predict 2026 cutoff via extrapolation
  4. Score admission probability based on user percentile vs predicted cutoff
  5. Compute ROI score  = avg_package_lpa / (annual_fee / 100_000)
  6. Classify tier: safe / target / reach
  7. Return a ranked results DataFrame ready for the UI
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path


# ── Constants ─────────────────────────────────────────────────────────────────

TIER_SAFE   = "safe"
TIER_TARGET = "target"
TIER_REACH  = "reach"

# Probability model: chance = 100 - k * gap
# gap = predicted_cutoff_2026 - user_percentile
# k controls how fast chance drops per percentile gap
PROB_SLOPE = 8.0          # chance drops 8 pp per 1-percentile gap above cutoff
PROB_FLOOR = 2            # minimum chance shown (never 0%)
PROB_CEILING = 98         # maximum chance shown (never 100%)


# ── Engine Class ──────────────────────────────────────────────────────────────

class PredictionEngine:
    """Load data and run predictions."""

    def __init__(self, data_path: str = "data.json"):
        self.data_path = Path(data_path)
        self._load_data()
        self._build_trend_table()

    # ── Data Loading ──────────────────────────────────────────────────────────

    def _load_data(self):
        """Parse data.json into normalised DataFrames."""
        with open(self.data_path) as f:
            raw = json.load(f)

        self.df_colleges  = pd.DataFrame(raw["colleges"])
        self.df_branches  = pd.DataFrame(raw["branches"])
        self.df_cutoffs   = pd.DataFrame(raw["cutoffs"])
        self.df_placements = pd.DataFrame(raw["placements"])
        self.df_fees      = pd.DataFrame(raw["fees"])

        # Convenience: latest placements and fees per branch
        self.df_latest_placements = (
            self.df_placements
            .sort_values("year", ascending=False)
            .groupby("branch_id", as_index=False)
            .first()
        )
        self.df_latest_fees = (
            self.df_fees
            .sort_values("year", ascending=False)
            .groupby("branch_id", as_index=False)
            .first()
        )

    # ── Trend Table ───────────────────────────────────────────────────────────

    def _build_trend_table(self):
        """
        For every (college_id, branch_id, category) triplet compute:
          - cutoff_2023, cutoff_2024, cutoff_2025  (CAP Round 1 only)
          - annual_shift   = mean year-on-year change
          - predicted_2026 = cutoff_2025 + annual_shift
        """
        # Use only Round 1 for trend analysis (most comparable)
        r1 = self.df_cutoffs[self.df_cutoffs["cap_round"] == 1].copy()

        # Pivot: rows = (college_id, branch_id, category), cols = year
        pivot = r1.pivot_table(
            index=["college_id", "branch_id", "category"],
            columns="year",
            values="cutoff_percentile",
        ).reset_index()

        # Rename year columns safely
        pivot.columns.name = None
        year_cols = [c for c in pivot.columns if isinstance(c, int)]
        rename_map = {y: f"cutoff_{y}" for y in year_cols}
        pivot.rename(columns=rename_map, inplace=True)

        available_years = sorted(year_cols)
        cutoff_col_names = [f"cutoff_{y}" for y in available_years]

        # Annual shift = linear slope across available years
        def compute_slope(row):
            vals = [row.get(col, np.nan) for col in cutoff_col_names]
            valid = [(i, v) for i, v in enumerate(vals) if not np.isnan(v)]
            if len(valid) < 2:
                return 0.0
            xs = np.array([x for x, _ in valid], dtype=float)
            ys = np.array([y for _, y in valid], dtype=float)
            return float(np.polyfit(xs, ys, 1)[0])

        pivot["annual_shift"] = pivot.apply(compute_slope, axis=1)

        # Latest known cutoff (most recent year)
        latest_col = f"cutoff_{max(available_years)}"
        pivot["cutoff_latest"] = pivot[latest_col]

        # Predicted 2026
        years_ahead = 2026 - max(available_years)
        pivot["predicted_2026"] = (
            pivot["cutoff_latest"] + pivot["annual_shift"] * years_ahead
        ).clip(0, 100).round(2)

        self.df_trends = pivot

    # ── Probability ───────────────────────────────────────────────────────────

    def _compute_chance(self, user_percentile: float, predicted_cutoff: float) -> int:
        """
        Linear model:
          gap > 0  → user is above cutoff → high chance
          gap < 0  → user is below cutoff → low chance
        """
        gap = user_percentile - predicted_cutoff
        chance = 50 + gap * PROB_SLOPE
        return int(np.clip(chance, PROB_FLOOR, PROB_CEILING))

    def _classify_tier(self, chance: int) -> str:
        if chance > 75:
            return TIER_SAFE
        if chance >= 40:
            return TIER_TARGET
        return TIER_REACH

    # ── ROI ───────────────────────────────────────────────────────────────────

    def _compute_roi(self, avg_package_lpa: float, annual_fee: float) -> float:
        """ROI = avg_package_lpa / (annual_fee / 1_00_000)"""
        if annual_fee <= 0:
            return 0.0
        return round(avg_package_lpa / (annual_fee / 100_000), 2)

    # ── Public: available options ─────────────────────────────────────────────

    def available_categories(self):
        return sorted(self.df_cutoffs["category"].unique().tolist())

    def available_branches(self):
        return sorted(self.df_branches["branch_name"].unique().tolist())

    def college_names(self):
        return self.df_colleges["short_name"].tolist()

    # ── Public: get raw cutoff trend for a college ────────────────────────────

    def get_trend_series(self, short_name: str, category: str = "OPEN") -> pd.Series:
        """
        Return a Series indexed by year (2023, 2024, 2025) for a given college.
        Used by the trend chart.
        """
        college = self.df_colleges[self.df_colleges["short_name"] == short_name]
        if college.empty:
            return pd.Series(dtype=float)
        college_id = college.iloc[0]["college_id"]

        mask = (
            (self.df_trends["college_id"] == college_id) &
            (self.df_trends["category"] == category)
        )
        row = self.df_trends[mask]
        if row.empty:
            return pd.Series(dtype=float)

        row = row.iloc[0]
        data = {}
        for col in row.index:
            if col.startswith("cutoff_") and col != "cutoff_latest":
                year = int(col.split("_")[1])
                val = row[col]
                if not np.isnan(val):
                    data[year] = val
        return pd.Series(data).sort_index()

    # ── Public: main predict ──────────────────────────────────────────────────

    def predict(
        self,
        user_percentile: float,
        category: str,
        branch_name: str,
    ) -> pd.DataFrame:
        """
        Core prediction function.

        Parameters
        ----------
        user_percentile : float  (e.g. 94.5)
        category        : str    (e.g. "OPEN")
        branch_name     : str    (e.g. "Computer Engineering")

        Returns
        -------
        DataFrame with one row per matching college, sorted by chance desc.
        Columns:
            college_id, short_name, branch_name, location, autonomous,
            cutoff_2023, cutoff_2024, cutoff_2025, annual_shift,
            predicted_2026, chance, tier,
            avg_package_lpa, highest_package_lpa, placement_pct,
            annual_fee, total_4yr_fee, scholarship_available,
            roi_score, top_recruiters
        """

        # Step 1: find branches matching the requested branch name
        matching_branches = self.df_branches[
            self.df_branches["branch_name"] == branch_name
        ][["branch_id", "college_id", "branch_name", "total_seats", "cap_seats"]]

        if matching_branches.empty:
            return pd.DataFrame()

        # Step 2: join trend data for the requested category
        trends_cat = self.df_trends[
            self.df_trends["category"] == category
        ][["college_id", "branch_id", "annual_shift", "predicted_2026",
           "cutoff_latest"] +
          [c for c in self.df_trends.columns if c.startswith("cutoff_2")]
        ]

        merged = matching_branches.merge(trends_cat, on=["college_id", "branch_id"], how="inner")

        if merged.empty:
            # Fallback: try OPEN category if chosen category has no data
            trends_open = self.df_trends[
                self.df_trends["category"] == "OPEN"
            ][["college_id", "branch_id", "annual_shift", "predicted_2026",
               "cutoff_latest"] +
              [c for c in self.df_trends.columns if c.startswith("cutoff_2")]
            ]
            merged = matching_branches.merge(trends_open, on=["college_id", "branch_id"], how="inner")

        if merged.empty:
            return pd.DataFrame()

        # Step 3: join college metadata
        merged = merged.merge(
            self.df_colleges[["college_id", "short_name", "location",
                               "autonomous", "naac_grade", "nirf_rank", "type"]],
            on="college_id",
            how="left",
        )

        # Step 4: join latest placements
        merged = merged.merge(
            self.df_latest_placements[[
                "branch_id", "avg_package_lpa", "highest_package_lpa",
                "median_package_lpa", "placement_pct", "top_recruiters"
            ]],
            on="branch_id",
            how="left",
        )

        # Step 5: join latest fees
        merged = merged.merge(
            self.df_latest_fees[[
                "branch_id", "annual_tuition_fee", "total_4yr_fee",
                "hostel_fee_annual", "scholarship_available"
            ]],
            on="branch_id",
            how="left",
        )

        # Step 6: compute chance, tier, ROI
        merged["chance"] = merged.apply(
            lambda r: self._compute_chance(user_percentile, r["predicted_2026"]),
            axis=1,
        )
        merged["tier"] = merged["chance"].apply(self._classify_tier)
        merged["roi_score"] = merged.apply(
            lambda r: self._compute_roi(
                r.get("avg_package_lpa", 0),
                r.get("annual_tuition_fee", 1),
            ),
            axis=1,
        )

        # Step 7: rename for UI clarity
        merged.rename(columns={
            "annual_tuition_fee": "annual_fee",
            "short_name": "short_name",
        }, inplace=True)

        # Step 8: sort by chance descending
        merged.sort_values("chance", ascending=False, inplace=True)
        merged.reset_index(drop=True, inplace=True)

        return merged
