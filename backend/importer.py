from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any
from time import perf_counter

import numpy as np
import pandas as pd

from .detector import detect
from .scoring import score
from .simulator import CHANNELS, UNITS


MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_ROWS = 50_000
MAX_COLUMNS = 64
PREVIEW_ROWS = 10
PROFILE_ID = "astra-sim-v1"
PROFILE_VERSION = "1.0"
EXPECTED_INTERVAL_SECONDS = 60.0

PROFILE_BOUNDS = {
    "battery_voltage": (0.0, 60.0),
    "battery_current": (-20.0, 50.0),
    "battery_temperature": (-100.0, 200.0),
    "signal_strength": (-200.0, 50.0),
    "attitude_error": (0.0, 180.0),
    "payload_temperature": (-100.0, 250.0),
    "propulsion_pressure": (0.0, 2_000.0),
    "radiation_level": (0.0, 100.0),
}

ASTRA_PROFILE = {
    "profile_id": PROFILE_ID,
    "profile_version": PROFILE_VERSION,
    "canonical_channels": list(CHANNELS),
    "units": UNITS,
    "required_channels": list(CHANNELS),
    "optional_channels": [],
    "expected_sampling_seconds": EXPECTED_INTERVAL_SECONDS,
    "detector_compatible": True,
    "minimum_observations": 5,
    "training_assumption": "The unchanged detector fits on the first 60% of this file; this segment must be a representative normal reference. ASTRA cannot verify this assumption.",
    "contract_note": "Prototype compatibility contract; not spacecraft certification.",
}


class ImportValidationError(ValueError):
    def __init__(self, message: str, *, code: str = "invalid_csv") -> None:
        super().__init__(message)
        self.code = code


def sanitize_filename(filename: str | None) -> str:
    leaf = PurePosixPath((filename or "recorded-telemetry.csv").replace("\\", "/")).name
    safe = re.sub(r"[^A-Za-z0-9._ -]", "_", leaf).strip(" .")
    if not safe:
        safe = "recorded-telemetry.csv"
    if not safe.lower().endswith(".csv"):
        safe = f"{safe}.csv"
    return safe[:120]


def parse_mapping(raw_mapping: str | None) -> dict[str, str]:
    if not raw_mapping:
        return {}
    try:
        mapping = json.loads(raw_mapping)
    except json.JSONDecodeError as exc:
        raise ImportValidationError("Column mapping must be valid JSON.", code="invalid_mapping") from exc
    if not isinstance(mapping, dict):
        raise ImportValidationError("Column mapping must be an object.", code="invalid_mapping")
    cleaned = {str(source): str(target) for source, target in mapping.items() if target}
    if len(set(cleaned.values())) != len(cleaned):
        raise ImportValidationError("Each canonical channel may be mapped only once.", code="duplicate_mapping")
    unknown = sorted(set(cleaned.values()) - set(CHANNELS))
    if unknown:
        raise ImportValidationError(f"Unsupported canonical channels: {', '.join(unknown)}.", code="invalid_mapping")
    return cleaned


def _formula_like(value: Any) -> bool:
    text = str(value).lstrip()
    return bool(text) and (
        text[0] in "=+@"
        or (text.startswith("-") and len(text) > 1 and not (text[1].isdigit() or text[1] == "."))
    )


def _read_csv(content: bytes) -> tuple[pd.DataFrame, list[str]]:
    if not content:
        raise ImportValidationError("The CSV file is empty.", code="empty_file")
    if len(content) > MAX_FILE_BYTES:
        raise ImportValidationError("The CSV exceeds the 10 MB upload limit.", code="file_too_large")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportValidationError("The CSV must use UTF-8 encoding.", code="invalid_encoding") from exc
    if not text.strip():
        raise ImportValidationError("The CSV file is empty.", code="empty_file")

    try:
        rows = csv.reader(io.StringIO(text))
        header = next(rows)
    except (csv.Error, StopIteration) as exc:
        raise ImportValidationError("The CSV does not contain a readable header.", code="invalid_header") from exc
    header = [item.strip() for item in header]
    if not header or any(not item for item in header):
        raise ImportValidationError("Every CSV column must have a header.", code="invalid_header")
    if len(header) > MAX_COLUMNS:
        raise ImportValidationError("The CSV exceeds the 64-column limit.", code="too_many_columns")
    duplicates = sorted({item for item in header if header.count(item) > 1})
    if duplicates:
        raise ImportValidationError(f"Duplicate CSV headers: {', '.join(duplicates)}.", code="duplicate_headers")

    try:
        count = 0
        for row in rows:
            if not row:
                continue
            count += 1
            if count > MAX_ROWS:
                raise ImportValidationError(f"The CSV exceeds the {MAX_ROWS:,}-row limit.", code="too_many_rows")
            if len(row) != len(header):
                raise ImportValidationError(f"Row {count + 1} has a different number of fields than the header.", code="malformed_csv")
    except csv.Error as exc:
        raise ImportValidationError("The CSV structure is malformed.", code="malformed_csv") from exc

    try:
        frame = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False, na_filter=False)
    except (pd.errors.ParserError, UnicodeError) as exc:
        raise ImportValidationError("The CSV structure is malformed.", code="malformed_csv") from exc
    if frame.empty:
        raise ImportValidationError("The CSV contains no telemetry rows.", code="empty_file")
    if len(frame) > MAX_ROWS:
        raise ImportValidationError(f"The CSV exceeds the {MAX_ROWS:,}-row limit.", code="too_many_rows")
    frame.columns = header
    return frame, header


def _numeric_columns(frame: pd.DataFrame, excluded: set[str]) -> tuple[list[str], dict[str, pd.Series], dict[str, int], list[str]]:
    numeric_columns: list[str] = []
    numeric: dict[str, pd.Series] = {}
    invalid_counts: dict[str, int] = {}
    formula_columns: list[str] = []
    for column in frame.columns:
        if column in excluded:
            continue
        values = frame[column].astype(str).str.strip()
        formulas = values.map(_formula_like)
        if formulas.any():
            formula_columns.append(column)
        converted = pd.to_numeric(values.mask(values.eq("")), errors="coerce")
        converted = converted.replace([np.inf, -np.inf], np.nan)
        nonempty = values.ne("")
        valid_count = int((converted.notna() & nonempty & ~formulas).sum())
        if valid_count:
            numeric_columns.append(column)
            numeric[column] = converted.mask(formulas)
            invalid_counts[column] = int((nonempty & (converted.isna() | formulas)).sum())
    return numeric_columns, numeric, invalid_counts, formula_columns


def _quality(timestamps: pd.Series, numeric: dict[str, pd.Series]) -> dict[str, Any]:
    deltas = timestamps.diff().dt.total_seconds()
    positive = deltas[deltas > 0]
    sampling = float(positive.median()) if not positive.empty else None
    gap_threshold = sampling * 1.5 if sampling else math.inf
    constant = []
    for name, values in numeric.items():
        finite = values.replace([np.inf, -np.inf], np.nan).dropna()
        if len(finite) and (finite.nunique() <= 1 or float(finite.std(ddof=0)) <= 1e-9):
            constant.append(name)
    return {
        "missing_value_count": int(sum(series.isna().sum() for series in numeric.values())),
        "duplicate_timestamp_count": int(timestamps.duplicated().sum()),
        "out_of_order_timestamp_count": int((deltas < 0).sum()),
        "estimated_gap_count": int((deltas > gap_threshold).sum()) if sampling else 0,
        "constant_channels": constant,
        "sampling_interval_seconds": sampling,
        "timestamp_continuity": bool(
            sampling is not None
            and not timestamps.duplicated().any()
            and not (deltas.dropna() <= 0).any()
            and not (deltas > gap_threshold).any()
        ),
    }


def _preview(frame: pd.DataFrame) -> list[dict[str, str]]:
    return [
        {column: str(value)[:160] for column, value in row.items()}
        for row in frame.head(PREVIEW_ROWS).to_dict(orient="records")
    ]


def _compatibility(
    mapping: dict[str, str],
    units_confirmed: bool,
    timestamps: pd.Series,
    mapped_numeric: dict[str, pd.Series],
    quality: dict[str, Any],
) -> tuple[str, list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    mapped_targets = set(mapping.values())
    missing_channels = [channel for channel in CHANNELS if channel not in mapped_targets]
    if missing_channels:
        warnings.append(f"Detector profile requires mappings for: {', '.join(missing_channels)}.")
    if not units_confirmed:
        warnings.append("Expected prototype units have not been confirmed.")
    if quality["duplicate_timestamp_count"]:
        warnings.append("Duplicate timestamps must be corrected before detector analysis.")
    if quality["out_of_order_timestamp_count"]:
        warnings.append("Out-of-order timestamps must be corrected before detector analysis.")
    if quality["estimated_gap_count"]:
        warnings.append("Telemetry gaps must be corrected before detector analysis.")
    sampling_matches = len(timestamps) >= 5 and bool(
        np.isclose(timestamps.diff().dt.total_seconds().dropna(), EXPECTED_INTERVAL_SECONDS, rtol=0, atol=1e-6).all()
    )
    if not sampling_matches:
        warnings.append(
            f"Detector profile requires at least 5 observations and a {EXPECTED_INTERVAL_SECONDS:g}-second sampling interval."
        )
    if quality["constant_channels"]:
        warnings.append(f"Constant or nearly constant channels: {', '.join(quality['constant_channels'])}.")

    for source, target in mapping.items():
        values = mapped_numeric.get(source)
        if values is None:
            errors.append(f"Mapped column '{source}' has no usable numeric values.")
            continue
        if values.isna().any() or not np.isfinite(values.dropna()).all():
            warnings.append(f"Mapped channel '{source}' contains missing, non-numeric or non-finite values.")
            continue
        lower, upper = PROFILE_BOUNDS[target]
        if ((values < lower) | (values > upper)).any():
            warnings.append(f"Mapped channel '{source}' contains values outside the {target} prototype bounds.")

    compatible = (
        not errors
        and not missing_channels
        and units_confirmed
        and quality["timestamp_continuity"]
        and sampling_matches
        and all(
            source in mapped_numeric
            and not mapped_numeric[source].isna().any()
            and np.isfinite(mapped_numeric[source]).all()
            and mapped_numeric[source].between(*PROFILE_BOUNDS[target]).all()
            for source, target in mapping.items()
        )
    )
    return ("compatible" if compatible else "visualisation_only"), errors, warnings


def process_recorded_csv(
    content: bytes,
    *,
    filename: str | None,
    timestamp_column: str | None = None,
    mission_column: str | None = None,
    mapping: dict[str, str] | None = None,
    units_confirmed: bool = False,
    seed: int = 42,
) -> dict[str, Any]:
    if filename and not filename.lower().endswith(".csv"):
        raise ImportValidationError("Only CSV files are accepted.", code="csv_required")
    frame, columns = _read_csv(content)
    timestamp_column = timestamp_column or ("timestamp" if "timestamp" in columns else "")
    if timestamp_column not in columns:
        return {
            "compatibility": "invalid",
            "validation": {"errors": ["Select a valid timestamp column."], "warnings": []},
            "columns": columns,
            "preview": _preview(frame),
            "import_metadata": {
                "sanitized_filename": sanitize_filename(filename),
                "file_size_bytes": len(content),
                "file_hash": hashlib.sha256(content).hexdigest(),
                "row_count": len(frame),
                "import_time": datetime.now(timezone.utc).isoformat(),
            },
        }

    timestamps = pd.to_datetime(frame[timestamp_column], utc=True, errors="coerce")
    bad_timestamps = int(timestamps.isna().sum())
    if bad_timestamps:
        return {
            "compatibility": "invalid",
            "validation": {"errors": [f"{bad_timestamps} timestamp value(s) could not be interpreted."], "warnings": []},
            "columns": columns,
            "preview": _preview(frame),
            "import_metadata": {
                "sanitized_filename": sanitize_filename(filename),
                "file_size_bytes": len(content),
                "file_hash": hashlib.sha256(content).hexdigest(),
                "row_count": len(frame),
                "import_time": datetime.now(timezone.utc).isoformat(),
            },
        }

    excluded = {timestamp_column}
    if mission_column in columns:
        excluded.add(str(mission_column))
    numeric_columns, numeric, invalid_counts, formula_columns = _numeric_columns(frame, excluded)
    if not numeric_columns:
        raise ImportValidationError("The CSV has no usable numeric telemetry channels.", code="no_numeric_channels")

    if mapping is None:
        mapping = {column: column for column in numeric_columns if column in CHANNELS}
    missing_sources = sorted(set(mapping) - set(columns))
    if missing_sources:
        raise ImportValidationError(f"Mapped columns not found: {', '.join(missing_sources)}.", code="invalid_mapping")
    quality = _quality(timestamps, numeric)
    compatibility, errors, warnings = _compatibility(mapping, units_confirmed, timestamps, numeric, quality)
    for column, count in invalid_counts.items():
        if count:
            warnings.append(f"{column}: {count} non-numeric value(s).")
    if formula_columns:
        warnings.append(f"Formula-like text was treated as non-numeric in: {', '.join(formula_columns)}.")

    mission_identifier = "RECORDED-IMPORT"
    if mission_column in columns:
        values = frame[str(mission_column)].astype(str).str.strip()
        mission_identifier = next((value[:80] for value in values if value), mission_identifier)

    start = timestamps.min()
    end = timestamps.max()
    import_metadata = {
        "sanitized_filename": sanitize_filename(filename),
        "file_size_bytes": len(content),
        "file_hash": hashlib.sha256(content).hexdigest(),
        "row_count": len(frame),
        "start_timestamp": start.isoformat(),
        "end_timestamp": end.isoformat(),
        "duration_seconds": float((end - start).total_seconds()),
        "sampling_interval_seconds": quality["sampling_interval_seconds"],
        "detected_numeric_channels": numeric_columns,
        "mapped_channels": mapping,
        "mission_identifier": mission_identifier,
        "import_time": datetime.now(timezone.utc).isoformat(),
        "profile_id": PROFILE_ID if compatibility == "compatible" else None,
        "profile_version": PROFILE_VERSION if compatibility == "compatible" else None,
        "compatibility_status": compatibility,
    }

    result: dict[str, Any] = {
        "compatibility": compatibility,
        "compatibility_label": (
            "Compatible for prototype analysis"
            if compatibility == "compatible"
            else "Visualisation only"
        ),
        "columns": columns,
        "numeric_columns": numeric_columns,
        "canonical_channels": list(CHANNELS),
        "profile": ASTRA_PROFILE,
        "mapping": mapping,
        "preview": _preview(frame),
        "data_quality": quality,
        "validation": {"errors": errors, "warnings": warnings},
        "import_metadata": import_metadata,
    }

    if compatibility == "compatible":
        detector_frame = pd.DataFrame({"timestamp": timestamps})
        reverse_mapping = {target: source for source, target in mapping.items()}
        for channel in CHANNELS:
            detector_frame[channel] = numeric[reverse_mapping[channel]].astype(float)
        detector_frame["fault_active"] = False
        detector_frame["fault_type"] = None
        detector_frame["injected_subsystem"] = None
        detector_frame["fault_start_index"] = None
        detector_frame["fault_start_timestamp"] = None
        detector_frame["ground_truth_event_id"] = None
        started = perf_counter()
        scored, primary, events = score(detect(detector_frame, seed))
        elapsed_ms = (perf_counter() - started) * 1000
        result["telemetry"] = [
            {
                "timestamp": row.timestamp.isoformat(),
                **{channel: float(getattr(row, channel)) for channel in CHANNELS},
                "anomaly_score": round(float(row.anomaly_score), 1),
                "is_anomaly": bool(row.is_anomaly),
                "risk_score": float(row.risk_score),
                "health_score": float(row.health_score),
                "severity": row.severity,
                "fault_active": False,
                "fault_type": None,
                "injected_subsystem": None,
                "fault_start_index": None,
                "fault_start_timestamp": None,
                "ground_truth_event_id": None,
            }
            for row in scored.itertuples()
        ]
        result["event"] = None if primary is None else primary.model_dump(mode="json")
        result["events"] = [event.model_dump(mode="json") for event in events]
        final_risk = max((row["risk_score"] for row in result["telemetry"]), default=0)
        result["metrics"] = {
            "processing_latency_ms": round(elapsed_ms, 2),
            "detected_event_count": len(events),
            "maximum_anomaly_score": max((row["anomaly_score"] for row in result["telemetry"]), default=0),
            "risk_score": final_risk,
            "health_score": round(100 - final_risk, 1),
        }
    else:
        display_columns = numeric_columns[:8]
        result["visualization_channels"] = display_columns
        result["telemetry"] = [
            {
                "timestamp": timestamp.isoformat(),
                **{
                    column: (None if pd.isna(numeric[column].iloc[index]) else float(numeric[column].iloc[index]))
                    for column in display_columns
                },
            }
            for index, timestamp in enumerate(timestamps)
        ]
        result["event"] = None
        result["events"] = []
        result["metrics"] = None
    return result
