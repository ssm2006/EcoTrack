"""
assistant.py
------------
The "smart" decision-making layer of EcoTrack.

Given a footprint breakdown and (optionally) the user's recent history,
this module decides which category is the biggest contributor and
returns a small set of prioritized, practical recommendations.

The logic is intentionally rule-based and transparent (no black-box ML)
so that every recommendation can be explained -- a key requirement for
a trustworthy personal-finance/lifestyle assistant.
"""

# Practical, real-world tip bank, organised by category.
# Each tip includes an estimated daily CO2e saving (kg) so the
# assistant can rank suggestions by impact.
TIP_BANK = {
    "transport": [
        {"tip": "Swap one car trip a week for public transport or cycling.",
         "saving": 1.5},
        {"tip": "Combine errands into a single trip to cut total distance driven.",
         "saving": 0.8},
        {"tip": "If you drive a petrol/diesel car, consider carpooling for your commute.",
         "saving": 2.0},
        {"tip": "For short distances (<3km), try walking or cycling instead of driving.",
         "saving": 0.5},
    ],
    "electricity": [
        {"tip": "Switch to LED bulbs and turn off devices instead of leaving them on standby.",
         "saving": 0.4},
        {"tip": "Run washing machines and dishwashers on full loads, using eco mode.",
         "saving": 0.3},
        {"tip": "Unplug chargers and appliances when not in use to avoid phantom load.",
         "saving": 0.2},
        {"tip": "If possible, shift heavy appliance use to off-peak hours or use a timer.",
         "saving": 0.25},
    ],
    "diet": [
        {"tip": "Try 1-2 plant-based ('meat-free') days per week.",
         "saving": 0.8},
        {"tip": "Reduce red meat portions and choose chicken or fish on some days.",
         "saving": 0.5},
        {"tip": "Buy local and seasonal produce to cut transport emissions in food.",
         "saving": 0.3},
        {"tip": "Plan meals to reduce food waste -- wasted food still carries its full footprint.",
         "saving": 0.2},
    ],
    "waste": [
        {"tip": "Separate recyclables (paper, plastic, glass, metal) from general waste.",
         "saving": 0.3},
        {"tip": "Start composting food scraps instead of sending them to landfill.",
         "saving": 0.2},
        {"tip": "Avoid single-use plastics by carrying a reusable bottle and bag.",
         "saving": 0.1},
    ],
}

# Friendly labels for display
CATEGORY_LABELS = {
    "transport": "Transport",
    "electricity": "Electricity",
    "diet": "Diet",
    "waste": "Waste",
}


def get_recommendations(breakdown, history=None, max_tips=3):
    """
    Decide which category to focus on and return prioritized tips.

    Decision logic
    ---------------
    1. Find the category with the highest absolute emission (the
       "biggest lever") -- improvements here have the most impact.
    2. If history is provided, also check which category has been
       *trending upward* over the last few entries, and flag it even
       if it isn't the single largest contributor today.
    3. Always include at least one tip from the top category, then
       fill remaining slots with the next-highest-impact tips across
       categories (by estimated saving).

    Parameters
    ----------
    breakdown : dict
        Output of carbon_calculator.calculate_footprint (without "total").
    history : list[dict], optional
        Previous footprint breakdowns (most recent last), used to
        detect upward trends.
    max_tips : int
        Maximum number of tips to return.

    Returns
    -------
    dict
        {
            "focus_category": str,
            "focus_reason": str,
            "tips": [ {"category": str, "tip": str, "saving": float}, ... ]
        }
    """
    categories = ["transport", "electricity", "diet", "waste"]
    values = {c: breakdown.get(c, 0) for c in categories}

    # Step 1: largest contributor today
    focus_category = max(values, key=values.get)
    focus_reason = (
        f"{CATEGORY_LABELS[focus_category]} is your largest source of "
        f"emissions today ({values[focus_category]} kg CO2e)."
    )

    # Step 2: check trends if history available (last 3 entries)
    if history and len(history) >= 2:
        trend_increases = {}
        recent = history[-3:]
        for c in categories:
            series = [h.get(c, 0) for h in recent] + [values[c]]
            if len(series) >= 2 and series[-1] > series[0]:
                trend_increases[c] = series[-1] - series[0]

        if trend_increases:
            trending_category = max(trend_increases, key=trend_increases.get)
            # Only override focus if the trend is meaningful and not
            # already the focus category
            if trending_category != focus_category and trend_increases[trending_category] > 0.2:
                focus_category = trending_category
                focus_reason = (
                    f"Your {CATEGORY_LABELS[focus_category].lower()} emissions "
                    f"have been increasing recently -- worth a closer look."
                )

    # Step 3: build prioritized tip list
    tips = []

    # Always lead with a tip from the focus category
    focus_tips = sorted(TIP_BANK[focus_category], key=lambda t: -t["saving"])
    if focus_tips:
        top = focus_tips[0]
        tips.append({"category": focus_category, "tip": top["tip"], "saving": top["saving"]})

    # Gather remaining candidate tips from all categories, ranked by saving
    all_candidates = []
    for c in categories:
        for t in TIP_BANK[c]:
            if c == focus_category and t == focus_tips[0]:
                continue
            all_candidates.append({"category": c, "tip": t["tip"], "saving": t["saving"]})

    all_candidates.sort(key=lambda t: -t["saving"])

    for t in all_candidates:
        if len(tips) >= max_tips:
            break
        tips.append(t)

    return {
        "focus_category": focus_category,
        "focus_label": CATEGORY_LABELS[focus_category],
        "focus_reason": focus_reason,
        "tips": tips,
    }


def get_summary_message(total_today, history):
    """
    Generate a short, context-aware summary message comparing today's
    footprint to the user's recent average.
    """
    if not history:
        return ("This is your first logged day. Keep logging daily to "
                "see trends and get more personalized tips!")

    past_totals = [h.get("total", 0) for h in history]
    avg = sum(past_totals) / len(past_totals)

    diff = total_today - avg
    if diff < -0.5:
        return (f"Great job! Today's footprint ({total_today} kg CO2e) is "
                f"lower than your recent average ({avg:.2f} kg CO2e). Keep it up!")
    elif diff > 0.5:
        return (f"Today's footprint ({total_today} kg CO2e) is higher than "
                f"your recent average ({avg:.2f} kg CO2e). Check the tips below "
                f"for quick wins.")
    else:
        return (f"Today's footprint ({total_today} kg CO2e) is about the same "
                f"as your recent average ({avg:.2f} kg CO2e). Steady progress!")
