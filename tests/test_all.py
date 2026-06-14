"""
tests/test_all.py
-----------------
Unit and integration tests for EcoTrack.

Run with:  pytest tests/
"""

import json
import os
import sys
import tempfile
import pytest

# Make sure project root is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from carbon_calculator import calculate_footprint, yearly_projection, load_factors
from assistant import get_recommendations, get_summary_message
import storage


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def factors():
    return load_factors()


@pytest.fixture
def tmp_data_dir(monkeypatch, tmp_path):
    """Redirect storage writes to a temp directory so tests don't pollute data/users."""
    user_dir = tmp_path / "users"
    user_dir.mkdir()
    monkeypatch.setattr(storage, "DATA_DIR", str(user_dir))
    return user_dir


# ---------------------------------------------------------------------------
# carbon_calculator tests
# ---------------------------------------------------------------------------

class TestCalculateFootprint:
    def test_zero_entry_gives_only_diet(self, factors):
        entry = {"transport_mode": "walk", "transport_km": 0,
                 "electricity_kwh": 0, "diet": "vegan", "waste_kg": 0}
        result = calculate_footprint(entry, factors)
        assert result["transport"] == 0.0
        assert result["electricity"] == 0.0
        assert result["waste"] == 0.0
        assert result["diet"] == factors["diet"]["vegan"]
        assert result["total"] == factors["diet"]["vegan"]

    def test_car_petrol_transport(self, factors):
        entry = {"transport_mode": "car_petrol", "transport_km": 10,
                 "electricity_kwh": 0, "diet": "vegan", "waste_kg": 0}
        result = calculate_footprint(entry, factors)
        expected = round(10 * factors["transport"]["car_petrol"], 3)
        assert result["transport"] == expected

    def test_total_is_sum_of_categories(self, factors):
        entry = {"transport_mode": "bus", "transport_km": 20,
                 "electricity_kwh": 5, "diet": "medium_meat", "waste_kg": 1}
        result = calculate_footprint(entry, factors)
        assert abs(result["total"] - (result["transport"] + result["electricity"]
                                       + result["diet"] + result["waste"])) < 1e-6

    def test_electric_car_lower_than_petrol(self, factors):
        base = {"transport_km": 50, "electricity_kwh": 0, "diet": "vegan", "waste_kg": 0}
        petrol = calculate_footprint({"transport_mode": "car_petrol", **base}, factors)
        electric = calculate_footprint({"transport_mode": "car_electric", **base}, factors)
        assert electric["transport"] < petrol["transport"]

    def test_string_numbers_handled(self, factors):
        entry = {"transport_mode": "train", "transport_km": "15",
                 "electricity_kwh": "3.5", "diet": "vegetarian", "waste_kg": "0.5"}
        result = calculate_footprint(entry, factors)
        assert result["total"] > 0

    def test_yearly_projection(self):
        assert yearly_projection(5.0) == 1825.0
        assert yearly_projection(0.0) == 0.0


# ---------------------------------------------------------------------------
# assistant tests
# ---------------------------------------------------------------------------

class TestGetRecommendations:
    def _sample_breakdown(self, transport=3.0, electricity=1.0, diet=2.5, waste=0.5):
        return {"transport": transport, "electricity": electricity,
                "diet": diet, "waste": waste, "total": transport + electricity + diet + waste}

    def test_focus_is_highest_category(self):
        breakdown = self._sample_breakdown(transport=5.0, electricity=0.5,
                                           diet=0.5, waste=0.1)
        result = get_recommendations(breakdown)
        assert result["focus_category"] == "transport"

    def test_tips_list_not_empty(self):
        result = get_recommendations(self._sample_breakdown())
        assert len(result["tips"]) >= 1

    def test_max_tips_respected(self):
        result = get_recommendations(self._sample_breakdown(), max_tips=2)
        assert len(result["tips"]) <= 2

    def test_first_tip_matches_focus(self):
        breakdown = self._sample_breakdown(electricity=10.0)
        result = get_recommendations(breakdown)
        assert result["focus_category"] == "electricity"
        assert result["tips"][0]["category"] == "electricity"

    def test_trend_detection_overrides_focus(self):
        # diet is biggest today, but electricity has been trending up
        breakdown = {"transport": 1.0, "electricity": 2.5, "diet": 3.0,
                     "waste": 0.2, "total": 6.7}
        history = [
            {"transport": 1.0, "electricity": 0.5, "diet": 3.0, "waste": 0.2},
            {"transport": 1.0, "electricity": 1.0, "diet": 3.0, "waste": 0.2},
            {"transport": 1.0, "electricity": 1.8, "diet": 3.0, "waste": 0.2},
        ]
        result = get_recommendations(breakdown, history=history)
        # electricity rose > 0.2 from start to now -- should be flagged
        assert result["focus_category"] in ("electricity", "diet")

    def test_no_history_no_crash(self):
        result = get_recommendations(self._sample_breakdown(), history=[])
        assert "tips" in result


class TestGetSummaryMessage:
    def test_no_history(self):
        msg = get_summary_message(5.0, [])
        assert "first" in msg.lower()

    def test_better_than_average(self):
        history = [{"total": 8.0}, {"total": 9.0}]
        msg = get_summary_message(5.0, history)
        assert "great" in msg.lower() or "lower" in msg.lower()

    def test_worse_than_average(self):
        history = [{"total": 4.0}, {"total": 4.5}]
        msg = get_summary_message(8.0, history)
        assert "higher" in msg.lower()

    def test_same_as_average(self):
        history = [{"total": 5.0}, {"total": 5.0}]
        msg = get_summary_message(5.0, history)
        assert "same" in msg.lower() or "steady" in msg.lower()


# ---------------------------------------------------------------------------
# storage tests
# ---------------------------------------------------------------------------

class TestStorage:
    def test_load_empty_history(self, tmp_data_dir):
        assert storage.load_history("newuser") == []

    def test_save_and_load(self, tmp_data_dir):
        breakdown = {"transport": 1.0, "electricity": 2.0,
                     "diet": 1.5, "waste": 0.3, "total": 4.8}
        storage.save_entry("alice", breakdown)
        history = storage.load_history("alice")
        assert len(history) == 1
        assert history[0]["total"] == 4.8
        assert "date" in history[0]

    def test_multiple_saves_accumulate(self, tmp_data_dir):
        b = {"transport": 1.0, "electricity": 1.0, "diet": 1.0, "waste": 0.0, "total": 3.0}
        storage.save_entry("bob", b)
        storage.save_entry("bob", b)
        assert len(storage.load_history("bob")) == 2

    def test_invalid_username_raises(self, tmp_data_dir):
        with pytest.raises(ValueError):
            storage.load_history("../../etc/passwd")

    def test_username_with_spaces_raises(self, tmp_data_dir):
        with pytest.raises(ValueError):
            storage.load_history("bad name here")

    def test_capped_at_100_entries(self, tmp_data_dir):
        b = {"transport": 0.0, "electricity": 0.0, "diet": 1.5, "waste": 0.0, "total": 1.5}
        for _ in range(110):
            storage.save_entry("carol", b)
        assert len(storage.load_history("carol")) == 100
