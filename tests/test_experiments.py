import csv
import io
import json
import statistics
import zipfile
from random import Random

import pytest

from tigrifes.experiments import export_zip, run_experiments
from tigrifes.machine import simulate_participants


@pytest.fixture(scope="module")
def data():
    return run_experiments()


def test_e1_totals_and_sample_standard_deviation(data):
    assert sum(row["count"] for row in data["e1"]["distribution"]) == 10_000
    assert sum(row["frequency"] for row in data["e1"]["distribution"]) == pytest.approx(1)
    profits = [r.profit for r in data["sequences"][2026]]
    assert data["e1"]["sample_stddev"] == statistics.stdev(profits)
    assert data["e1"]["mean_profit"] == pytest.approx(data["e1"]["rtp"] - 1)


def test_e2_reuses_e1_and_records_correct_checkpoints(data):
    assert data["e2"]["reproduced"] is True
    for row in data["e2"]["checkpoints"]:
        for count in (100, 1000, 10000):
            expected = statistics.mean(r.profit for r in data["sequences"][row["seed"]][:count])
            assert row[f"n{count}"] == expected
    assert data["e2"]["checkpoints"][1]["n10000"] == data["e1"]["mean_profit"]


def test_e3_categories_and_continuous_rng(data):
    e3 = data["e3"]
    assert e3["gain"] + e3["tie"] + e3["loss"] == 100
    assert e3["exhausted"] <= e3["loss"]
    assert e3["participants"] == simulate_participants(Random(42))
    for participant in e3["participants"]:
        assert participant["rounds"] <= 500
        assert participant["rounds"] == 500 or participant["balance"] == 0
        assert participant["trajectory"][-1] == participant["balance"]


def test_e4_counts_all_consecutive_pairs(data):
    assert sum(r["pairs"] for r in data["e4"]) == 9999
    expected = sum(r.prize > 0 for r in data["sequences"][2026][1:])
    assert sum(r["prizes"] for r in data["e4"]) == expected


def test_e5_same_outcomes_and_fractional_prizes(data):
    base, enhanced = data["e5"]
    assert base["prize_frequency"] == enhanced["prize_frequency"]
    assert enhanced["observed_prize"] == pytest.approx(base["observed_prize"] * 1.1)
    assert enhanced["observed_profit"] == pytest.approx(enhanced["observed_prize"] - 1)
    assert enhanced["theoretical_rtp"] == .924
    assert enhanced["theoretical_profit"] == -.076


def test_download_has_raw_data_metadata_and_exportable_charts():
    with zipfile.ZipFile(io.BytesIO(export_zip())) as archive:
        metadata = json.loads(archive.read("metadata.json"))
        assert metadata["seed_e3"] == 42
        assert metadata["e4_e5_reuse_e1"] is True
        assert set(metadata["dependencies"]) == {"Jinja2", "matplotlib"}
        rows = list(csv.DictReader(io.StringIO(archive.read("rodadas_semente_2026.csv").decode("utf-8-sig"))))
        assert len(rows) == 10_000
        assert sum(int(r["profit"]) for r in rows) == -1315
        for name in ("frequencies", "convergence", "balances"):
            assert archive.read(f"graficos/{name}.png").startswith(b"\x89PNG")
            assert b"<svg" in archive.read(f"graficos/{name}.svg")
