from pathlib import Path

import pytest

from src.data import pick_population_path


class _FakeCfg:
    def __init__(self, data, root):
        self.data = data
        self.root = Path(root)

    def resolve(self, rel):
        return self.root / rel


def test_pick_real_returns_existing(tmp_path, monkeypatch):
    monkeypatch.delenv("LOWALT_DATA_MODE", raising=False)
    real = tmp_path / "worldpop.tif"
    real.write_bytes(b"x")
    cfg = _FakeCfg({"mode": "real", "population_tif": "worldpop.tif",
                    "synthetic_tif": "synthetic.tif"}, tmp_path)
    assert pick_population_path(cfg) == real


def test_pick_real_missing_raises_instead_of_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("LOWALT_DATA_MODE", raising=False)
    cfg = _FakeCfg({"mode": "real", "population_tif": "worldpop.tif",
                    "synthetic_tif": "synthetic.tif"}, tmp_path)
    with pytest.raises(FileNotFoundError) as exc:
        pick_population_path(cfg)
    msg = str(exc.value)
    assert "LOWALT_DATA_MODE" in msg
    assert "synthetic" in msg


def test_pick_synthetic_mode(tmp_path, monkeypatch):
    monkeypatch.delenv("LOWALT_DATA_MODE", raising=False)
    syn = tmp_path / "synthetic.tif"
    syn.write_bytes(b"x")
    cfg = _FakeCfg({"mode": "synthetic", "population_tif": "missing.tif",
                    "synthetic_tif": "synthetic.tif"}, tmp_path)
    assert pick_population_path(cfg) == syn


def test_env_override_to_synthetic(tmp_path, monkeypatch):
    syn = tmp_path / "synthetic.tif"
    syn.write_bytes(b"x")
    cfg = _FakeCfg({"mode": "real", "population_tif": "missing.tif",
                    "synthetic_tif": "synthetic.tif"}, tmp_path)
    monkeypatch.setenv("LOWALT_DATA_MODE", "synthetic")
    assert pick_population_path(cfg) == syn


def test_unknown_mode_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("LOWALT_DATA_MODE", raising=False)
    cfg = _FakeCfg({"mode": "whatever", "population_tif": "a.tif",
                    "synthetic_tif": "b.tif"}, tmp_path)
    with pytest.raises(ValueError):
        pick_population_path(cfg)
