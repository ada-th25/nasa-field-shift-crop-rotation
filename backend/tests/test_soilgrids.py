"""Tests for the SoilGrids client's retry behaviour, added after live
testing found the REST query endpoint sometimes returns a valid 200 with
every property null for a point that resolves fine elsewhere (see
docs/algorithm.md section 13/15). Mocks the network call so these don't
depend on ISRIC's live, sometimes-flaky response."""
from unittest.mock import patch

import app.data.soilgrids as soilgrids_module
from app.data.soilgrids import fetch_soilgrids

NULL_RESPONSE = {
    "properties": {
        "layers": [
            {"name": name, "depths": [{"label": "0-5cm", "values": {"mean": None}}]}
            for name in ("clay", "sand", "phh2o", "soc")
        ]
    }
}


def _response_with_soc(soc_tenths: int):
    return {
        "properties": {
            "layers": [
                {"name": "clay", "depths": [{"label": "0-5cm", "values": {"mean": None}}]},
                {"name": "sand", "depths": [{"label": "0-5cm", "values": {"mean": None}}]},
                {"name": "phh2o", "depths": [{"label": "0-5cm", "values": {"mean": None}}]},
                {"name": "soc", "depths": [{"label": "0-5cm", "values": {"mean": soc_tenths}}]},
            ]
        }
    }


def _isolate_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(soilgrids_module, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(soilgrids_module.time, "sleep", lambda *_: None)  # don't actually wait in tests


def test_retries_and_recovers_a_later_success(tmp_path, monkeypatch):
    _isolate_cache(tmp_path, monkeypatch)
    responses = [NULL_RESPONSE, NULL_RESPONSE, _response_with_soc(490)]
    with patch.object(soilgrids_module, "_query_soilgrids", side_effect=responses) as mock_query:
        result = fetch_soilgrids(42.03, -93.63, use_cache=False)
    assert result["soc_g_kg"] == 49.0
    assert mock_query.call_count == 3


def test_gives_up_after_max_retries_and_returns_null(tmp_path, monkeypatch):
    _isolate_cache(tmp_path, monkeypatch)
    with patch.object(soilgrids_module, "_query_soilgrids", return_value=NULL_RESPONSE) as mock_query:
        result = fetch_soilgrids(6.52, 3.38, use_cache=False, max_retries=2)
    assert result["soc_g_kg"] is None
    assert mock_query.call_count == 1 + 2  # first attempt + max_retries


def test_no_retry_needed_when_first_response_has_data(tmp_path, monkeypatch):
    _isolate_cache(tmp_path, monkeypatch)
    with patch.object(soilgrids_module, "_query_soilgrids", return_value=_response_with_soc(150)) as mock_query:
        result = fetch_soilgrids(42.03, -93.63, use_cache=False)
    assert result["soc_g_kg"] == 15.0
    assert mock_query.call_count == 1


def test_cache_hit_skips_the_network_entirely(tmp_path, monkeypatch):
    _isolate_cache(tmp_path, monkeypatch)
    cache_file = tmp_path / "soilgrids_42.03_-93.63.json"
    import json
    cache_file.write_text(json.dumps(_response_with_soc(200)))

    with patch.object(soilgrids_module, "_query_soilgrids") as mock_query:
        result = fetch_soilgrids(42.03, -93.63, use_cache=True)
    assert result["soc_g_kg"] == 20.0
    mock_query.assert_not_called()
