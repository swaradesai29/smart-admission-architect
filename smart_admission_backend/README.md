# Smart Admission Architect — Backend

A Streamlit + Pandas prediction engine for MHT-CET 2026 college admissions.

---

## Folder Structure

```
backend/
├── app.py              ← Main Streamlit app (entry point)
├── engine.py           ← Prediction engine (data loading, trend calc, probability)
├── ui_components.py    ← All Streamlit UI rendering functions
├── style.css           ← Custom CSS for Streamlit
├── data.json           ← Dummy data (colleges, cutoffs, placements, fees)
├── requirements.txt    ← Python dependencies
└── README.md
```

---

## Setup

### 1. Make sure Python 3.10+ is installed
```bash
python --version
```

### 2. Create a virtual environment (recommended)
```bash
python -m venv venv

# Activate on Windows:
venv\Scripts\activate

# Activate on Mac/Linux:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Place data.json in the same folder
Make sure `data.json` is in the `backend/` folder alongside `app.py`.

### 5. Run the app
```bash
streamlit run app.py
```

The app will open automatically at `http://localhost:8501`

---

## How It Works

### engine.py — Prediction Engine

| Step | What it does |
|------|-------------|
| Load | Reads `data.json` into 5 Pandas DataFrames |
| Trend | Pivots cutoff data, fits a linear slope per college/branch/category across 2023–2025 |
| Predict | Extrapolates 2026 cutoff = cutoff_2025 + annual_shift |
| Probability | `chance = 50 + (user_percentile - predicted_cutoff) × 8` clamped to 2–98% |
| ROI | `avg_package_lpa / (annual_fee / 1,00,000)` |
| Tier | safe (>75%), target (40–75%), reach (<40%) |

### ui_components.py — UI Layer

| Function | Renders |
|----------|---------|
| `render_header()` | Animated gradient hero banner |
| `render_input_panel()` | Percentile / Category / Branch inputs |
| `render_sidebar_filters()` | Tier, location, autonomous filters |
| `render_metrics()` | 4 summary metric cards |
| `render_college_cards()` | Styled dataframe + expandable detail cards |
| `render_roi_chart()` | Horizontal Plotly bar chart |
| `render_trend_chart()` | Multi-line Plotly trend chart |
| `render_compare_matrix()` | Side-by-side table + grouped bar chart |

---

## Customising Dummy Data

Edit `data.json` to add more colleges, update cutoffs, or change fees/placements.
The engine will automatically pick up changes on the next run (it's cached per session).

---

## Next Steps (when you have real data)

1. Replace `data.json` with data scraped from CET Cell PDFs
2. Add a PostgreSQL/SQLite database and swap `engine._load_data()` to read from it
3. Add user authentication with `streamlit-authenticator`
4. Deploy on Streamlit Community Cloud (free) — just push to GitHub and connect
