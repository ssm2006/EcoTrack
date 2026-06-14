# 🌍 EcoTrack — Personal Carbon Footprint Assistant

EcoTrack is a smart, dynamic web assistant that helps individuals **understand, track, and reduce their personal carbon footprint** through simple daily logging and personalized, actionable insights.

---

## Chosen Vertical

**Sustainability / Personal Climate Action**

---

## Approach & Logic

### Architecture

```
ecotrack/
├── app.py                  # Flask web application (routes, rendering)
├── carbon_calculator.py    # Footprint calculation logic
├── assistant.py            # Smart recommendation engine
├── storage.py              # Per-user JSON history storage
├── data/
│   └── factors.json        # Emission factors (easily updatable)
├── templates/              # Jinja2 HTML templates
├── static/style.css        # Responsive CSS
└── tests/test_all.py       # 22-test pytest suite
```

### How Calculation Works

The user inputs four simple data points each day:

| Category     | Input                          | Emission Factor Source          |
|--------------|--------------------------------|---------------------------------|
| Transport    | Mode + km traveled             | Per-mode kg CO2e/km             |
| Electricity  | kWh consumed                   | 0.475 kg CO2e/kWh (avg grid)   |
| Diet         | Eating pattern (vegan→hi-meat) | Daily average kg CO2e/day      |
| Waste        | kg of unsorted waste           | 0.57 kg CO2e/kg                |

Total daily footprint = sum of all four categories.

### Smart Assistant Logic

The recommendation engine in `assistant.py` uses a transparent, rule-based decision tree:

1. **Biggest lever first**: Identifies the category with the highest absolute CO2e contribution — this is where change has the most impact.
2. **Trend detection**: If the user has history (≥ 2 previous entries), the engine also checks which category has been *increasing most* over recent days. If a fast-growing category differs from the top contributor and the rise is meaningful (> 0.2 kg CO2e), the engine flags that instead.
3. **Ranked tips**: From a curated tip bank, it picks the highest-impact tip for the focus category first, then fills remaining slots from all categories ranked by estimated daily CO2e saving.

This approach is:
- **Transparent** — every recommendation can be explained in plain English
- **Adaptive** — uses personal history rather than generic advice
- **Prioritised** — focuses effort where it makes the most difference

### Dashboard & Trend Visualisation

A personal dashboard (`/dashboard/<username>`) shows:
- A line chart of daily totals over time (using Chart.js)
- A table of recent entries with per-category breakdown
- Running daily average

---

## How to Run

### Prerequisites

- Python 3.9+
- pip

### Install & Start

```bash
git clone https://github.com/<your-username>/ecotrack.git
cd ecotrack
pip install -r requirements.txt
python app.py
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in your browser.

### Run Tests

```bash
pytest tests/ -v
```

All 22 tests cover the calculator, assistant logic, and storage layer.

---

## Assumptions Made

- **Emission factors** are global averages. Regional grid mix varies — the `data/factors.json` file can be updated without touching code.
- **Diet** emissions represent a full-day average for the chosen eating pattern, not individual meals.
- **Electricity** input is a user estimate; households typically use 8–15 kWh/day.
- **No authentication**: users are identified by a self-chosen nickname stored in a local JSON file. This is a demo; production should use a database and proper auth.
- **Single-user server**: `python app.py` uses Flask's development server. For production, use Gunicorn or similar.

---

## Evaluation Criteria Coverage

| Area            | What's implemented                                                                 |
|-----------------|------------------------------------------------------------------------------------|
| Code Quality    | Modular design (calculator / assistant / storage separated), docstrings throughout |
| Security        | Path traversal protection in storage, input sanitisation in app.py                 |
| Efficiency      | O(1) lookups from in-memory factors dict; history capped at 100 entries           |
| Testing         | 22 pytest unit + integration tests across all three core modules                  |
| Accessibility   | Semantic HTML (`<label>`, `<main>`, `<nav>`, `<header>`), good colour contrast    |
