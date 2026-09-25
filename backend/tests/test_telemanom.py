import csv

import numpy as np
import pytest

from backend.data.telemanom import TelemanomDataError, load_channel, parse_anomaly_ranges


def make_fixture(tmp_path):
    (tmp_path / "train").mkdir()
    (tmp_path / "test").mkdir()
    np.save(tmp_path / "train" / "P-1.npy", np.zeros((8, 2)))
    np.save(tmp_path / "test" / "P-1.npy", np.zeros((10, 2)))
    with (tmp_path / "labeled_anomalies.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["chan_id", "spacecraft", "anomaly_sequences"])
        writer.writeheader()
        writer.writerow({"chan_id": "P-1", "spacecraft": "SMAP", "anomaly_sequences": "[[2, 4], [7, 7]]"})


def test_range_parser_and_canonical_telemanom_loader(tmp_path):
    make_fixture(tmp_path)
    assert parse_anomaly_ranges("[[2, 4]]", 10) == [(2, 4)]
    train, test = load_channel(tmp_path, "P-1")
    assert train.units == {}
    assert not train.frame.ground_truth_anomaly.any()
    assert test.frame.ground_truth_anomaly.tolist() == [
        False, False, True, True, True, False, False, True, False, False
    ]
    assert test.frame.timestamp.isna().all()
    assert test.provenance["anonymized"] is True


def test_missing_and_malformed_telemanom_data(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_channel(tmp_path, "P-1")
    with pytest.raises(TelemanomDataError):
        parse_anomaly_ranges("not a list")
    with pytest.raises(TelemanomDataError):
        parse_anomaly_ranges("[[2, 20]]", 10)
