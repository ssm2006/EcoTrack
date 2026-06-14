"""
app.py
------
EcoTrack: A Personal Carbon Footprint Assistant.

A small Flask web app that lets a user log their daily activities
(transport, electricity, diet, waste), calculates an estimated daily
carbon footprint, stores history per user, and returns a smart,
rule-based set of personalized tips to help reduce emissions.

Run locally:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, redirect, url_for, flash

from carbon_calculator import calculate_footprint, load_factors, yearly_projection
from assistant import get_recommendations, get_summary_message
import storage

app = Flask(__name__)
app.secret_key = "ecotrack-demo-secret-key"  # fine for a demo; use env var in production

FACTORS = load_factors()


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        username = (request.form.get("username") or "guest").strip().lower() or "guest"
        # sanitize for safe filenames -- replace anything not alnum/_/- with _
        username = "".join(c if (c.isalnum() or c in "-_") else "_" for c in username)[:40]

        entry = {
            "transport_mode": request.form.get("transport_mode", "car_petrol"),
            "transport_km": request.form.get("transport_km", 0),
            "electricity_kwh": request.form.get("electricity_kwh", 0),
            "diet": request.form.get("diet", "medium_meat"),
            "waste_kg": request.form.get("waste_kg", 0),
        }

        try:
            breakdown = calculate_footprint(entry, FACTORS)
        except (ValueError, TypeError):
            flash("Please enter valid numbers for all fields.")
            return redirect(url_for("index"))

        history = storage.load_history(username)
        recommendations = get_recommendations(breakdown, history)
        summary = get_summary_message(breakdown["total"], history)
        storage.save_entry(username, breakdown)

        return render_template(
            "result.html",
            username=username,
            breakdown=breakdown,
            yearly=yearly_projection(breakdown["total"]),
            recommendations=recommendations,
            summary=summary,
        )

    return render_template("index.html", factors=FACTORS)


@app.route("/dashboard/<username>")
def dashboard(username):
    history = storage.load_history(username)
    if not history:
        flash(f"No history found for '{username}' yet. Log an entry first!")
        return redirect(url_for("index"))

    labels = [h["date"] for h in history]
    totals = [h["total"] for h in history]

    avg = round(sum(totals) / len(totals), 2)
    latest = history[-1]

    return render_template(
        "dashboard.html",
        username=username,
        history=history,
        labels=labels,
        totals=totals,
        avg=avg,
        latest=latest,
    )


@app.route("/about")
def about():
    return render_template("about.html")


if __name__ == "__main__":
    app.run(debug=True)
