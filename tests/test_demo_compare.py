from services.science_api.demo_compare import compare_barind_demo


def test_barind_demo_has_three_conditional_pathways_and_real_evidence():
    result = compare_barind_demo()
    assert result["status"] == "conditional"
    assert len(result["results"]) == 3
    assert result["evidence"]["provider"] == "NASA Langley Research Center POWER"
    assert result["evidence"]["ids"]
    assert all(item["model_run_id"] for item in result["results"])
    assert all(item["calendar_status"] != "verified_local" for item in result["results"])


def test_scenario_recomputes_and_lower_allowance_never_increases_irrigation():
    baseline = compare_barind_demo(irrigation_allowance_mm=700)
    constrained = compare_barind_demo(irrigation_allowance_mm=350)
    assert baseline["model_run_id"] != constrained["model_run_id"]
    before = {item["id"]: item["irrigation_gross_mm"] for item in baseline["results"]}
    after = {item["id"]: item["irrigation_gross_mm"] for item in constrained["results"]}
    assert all(after[key] <= before[key] for key in before)


def test_rainfall_stress_recomputes_run_identity():
    baseline = compare_barind_demo(rainfall_multiplier=1.0)
    dry = compare_barind_demo(rainfall_multiplier=0.7)
    assert baseline["model_run_id"] != dry["model_run_id"]
    assert dry["scenario"]["kind"] == "hypothetical_stress_test"
