import os
from time import perf_counter

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .detector import detect
from .schemas import Metadata, Metrics, SimulationRequest, SimulationResponse, TelemetryPoint
from .scoring import score
from .simulator import CHANNELS, UNITS, simulate


LOCAL_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
ADDITIONAL_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
    if origin.strip()
]
ALLOWED_ORIGINS = list(dict.fromkeys([*LOCAL_ORIGINS, *ADDITIONAL_ORIGINS]))


app = FastAPI(title="ASTRA Simulated Telemetry API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"^https://[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.vercel\.app$",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
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


@app.post("/api/simulate", response_model=SimulationResponse)
def run_simulation(request: SimulationRequest) -> SimulationResponse:
    started = perf_counter()
    frame = simulate(request.scenario, request.points, request.seed)
    scored, event, event_count = score(detect(frame, request.seed))
    telemetry = [
        TelemetryPoint(**{
            "timestamp": row.timestamp,
            **{channel: round(float(getattr(row, channel)), 3) for channel in CHANNELS},
            "anomaly_score": round(float(row.anomaly_score), 1),
            "is_anomaly": bool(row.is_anomaly),
            "risk_score": float(row.risk_score),
            "health_score": float(row.health_score),
            "severity": row.severity,
        })
        for row in scored.itertuples()
    ]
    final_risk = max((point.risk_score for point in telemetry), default=0)
    return SimulationResponse(
        metadata=Metadata(scenario=request.scenario, points=request.points, seed=request.seed, units=UNITS),
        telemetry=telemetry,
        event=event,
        metrics=Metrics(
            processing_latency_ms=round((perf_counter() - started) * 1000, 2),
            detected_event_count=event_count,
            maximum_anomaly_score=round(max((point.anomaly_score for point in telemetry), default=0), 1),
            risk_score=final_risk,
            health_score=round(100 - final_risk, 1),
        ),
    )
