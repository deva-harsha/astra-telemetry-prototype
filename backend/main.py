import os
from time import perf_counter

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from .detector import detect
from .importer import ASTRA_PROFILE, ImportValidationError, MAX_FILE_BYTES, parse_mapping, process_recorded_csv
from .schemas import DataQuality, Metadata, Metrics, SimulationRequest, SimulationResponse, TelemetryPoint
from .scoring import score
from .simulator import CHANNELS, UNITS, simulate


LOCAL_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]
ADDITIONAL_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
ALLOWED_ORIGINS = list(dict.fromkeys([*LOCAL_ORIGINS, *ADDITIONAL_ORIGINS]))

app = FastAPI(title="ASTRA Simulated Telemetry API", version="0.3.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.vercel\.app$",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=[
        "Content-Type",
        "X-ASTRA-Filename",
        "X-ASTRA-Timestamp-Column",
        "X-ASTRA-Mission-Column",
        "X-ASTRA-Mapping",
        "X-ASTRA-Units-Confirmed",
    ],
)


def calculate_data_quality(frame: pd.DataFrame) -> DataQuality:
    timestamps = pd.to_datetime(frame["timestamp"], utc=True)
    deltas = timestamps.diff().dt.total_seconds().dropna()
    expected_seconds = 60
    return DataQuality(
        timestamp_continuity=bool((deltas == expected_seconds).all()),
        missing_value_count=int(frame[list(CHANNELS)].isna().sum().sum()),
        telemetry_gap_count=int((deltas > expected_seconds).sum()),
        stale_observation_count=int((deltas <= 0).sum()),
        available_channels=len(CHANNELS),
        data_source="ASTRA deterministic simulator",
    )


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ASTRA", "source": "simulated telemetry"}


@app.get("/api/scenarios")
def scenarios() -> list[dict[str, str]]:
    return [
        {"id": "normal", "label": "Normal Operation"},
        {"id": "thermal_fault", "label": "Thermal Fault"},
        {"id": "power_fault", "label": "Power Fault"},
    ]


@app.get("/api/import/profile")
def import_profile() -> dict:
    return ASTRA_PROFILE


@app.post("/api/import/telemetry")
async def import_telemetry(request: Request) -> dict:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type not in {"text/csv", "application/csv", "application/vnd.ms-excel"}:
        raise HTTPException(status_code=415, detail={"code": "csv_required", "message": "Upload a CSV file."})
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_size = int(content_length)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail={"code": "invalid_content_length", "message": "Content-Length must be an integer."},
            ) from exc
        if declared_size > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail={"code": "file_too_large", "message": "The CSV exceeds the 10 MB upload limit."})
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_FILE_BYTES:
            raise HTTPException(status_code=413, detail={"code": "file_too_large", "message": "The CSV exceeds the 10 MB upload limit."})
        chunks.append(chunk)
    try:
        raw_mapping = request.headers.get("x-astra-mapping")
        mapping = parse_mapping(raw_mapping) if raw_mapping is not None else None
        return process_recorded_csv(
            b"".join(chunks),
            filename=request.headers.get("x-astra-filename"),
            timestamp_column=request.headers.get("x-astra-timestamp-column"),
            mission_column=request.headers.get("x-astra-mission-column"),
            mapping=mapping,
            units_confirmed=request.headers.get("x-astra-units-confirmed", "").lower() == "true",
        )
    except ImportValidationError as exc:
        status = 413 if exc.code in {"file_too_large", "too_many_rows"} else 400
        raise HTTPException(status_code=status, detail={"code": exc.code, "message": str(exc)}) from exc


@app.post("/api/simulate", response_model=SimulationResponse)
def run_simulation(request: SimulationRequest) -> SimulationResponse:
    started = perf_counter()
    frame = simulate(request.scenario, request.points, request.seed)
    scored, event, events = score(detect(frame, request.seed))
    telemetry = [
        TelemetryPoint(**{
            "timestamp": row.timestamp,
            **{channel: round(float(getattr(row, channel)), 3) for channel in CHANNELS},
            "anomaly_score": round(float(row.anomaly_score), 1),
            "is_anomaly": bool(row.is_anomaly),
            "risk_score": float(row.risk_score),
            "health_score": float(row.health_score),
            "severity": row.severity,
            "fault_active": bool(row.fault_active),
            "fault_type": row.fault_type,
            "injected_subsystem": row.injected_subsystem,
            "fault_start_index": None if pd.isna(row.fault_start_index) else int(row.fault_start_index),
            "fault_start_timestamp": row.fault_start_timestamp,
            "ground_truth_event_id": None if pd.isna(row.ground_truth_event_id) else str(row.ground_truth_event_id),
        })
        for row in scored.itertuples()
    ]
    final_risk = max((point.risk_score for point in telemetry), default=0)
    onset = None if request.scenario == "normal" else int(request.points * 0.6)
    return SimulationResponse(
        metadata=Metadata(
            scenario=request.scenario,
            points=request.points,
            seed=request.seed,
            units=UNITS,
            fault_start_index=onset,
            fault_start_timestamp=None if onset is None else frame.iloc[onset].timestamp,
        ),
        telemetry=telemetry,
        event=event,
        events=events,
        data_quality=calculate_data_quality(frame),
        metrics=Metrics(
            processing_latency_ms=round((perf_counter() - started) * 1000, 2),
            detected_event_count=len(events),
            maximum_anomaly_score=round(max((point.anomaly_score for point in telemetry), default=0), 1),
            risk_score=final_risk,
            health_score=round(100 - final_risk, 1),
        ),
    )
