"""Phase 1 tests: configuration loads and has the values we need."""

from src.config import PROJECT_ROOT, get_path, load_config


def test_config_loads():
    cfg = load_config()
    assert cfg["city"]["name"] == "Varanasi"


def test_city_centre_is_near_varanasi():
    city = load_config()["city"]
    assert 25.0 < city["center_lat"] < 25.6
    assert 82.7 < city["center_lon"] < 83.2


def test_four_provenance_labels():
    labels = set(load_config()["provenance"])
    assert labels == {"REAL", "SIMULATED", "DEMO", "USER"}


def test_data_folders_exist():
    for key in ["raw", "processed", "simulated", "demo"]:
        assert get_path(key).is_dir(), f"missing folder for {key}"
    assert (PROJECT_ROOT / "config.yaml").exists()
