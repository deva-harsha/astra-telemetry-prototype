# ASTRA

ASTRA is a local, ground-based spacecraft telemetry anomaly-detection and operator decision-support prototype. All telemetry is explicitly simulated. ASTRA does not connect to or control a spacecraft, predict an exact failure time, or confirm a root-cause diagnosis.

## Start on Windows PowerShell

Open PowerShell in the project root (`C:\ASTRA`). The pre-existing root `.venv` points to a missing Python installation. This workspace already has a working `backend\.venv`; the commands below start it directly.

**Terminal 1 — backend**

```powershell
cd C:\ASTRA
.\backend\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

To recreate `backend\.venv` on this host, use the bundled Python runtime:

```powershell
cd C:\ASTRA
& 'C:\Users\vbitr\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
```

On another machine with Python 3.12 installed, use `py -3.12 -m venv backend\.venv` in place of the bundled-runtime command.

**Terminal 2 — frontend**

```powershell
cd C:\ASTRA\frontend
npm ci
npm run dev -- --host localhost --port 5173
```

Open `http://localhost:5173`. The API documentation is at `http://127.0.0.1:8000/docs`.

## Test and build

```powershell
cd C:\ASTRA
.\backend\.venv\Scripts\python.exe -m pytest backend\tests -q
cd C:\ASTRA\frontend
npm run build
```

## API

`GET /api/health` reports API status. `GET /api/scenarios` lists the three scenarios. `POST /api/simulate` accepts:

```json
{"scenario":"normal","points":180,"seed":42}
```

Scenarios are `normal`, `thermal_fault`, and `power_fault`; `points` may be 60–1000. Timestamps begin at a fixed UTC date, one minute apart. The seed makes telemetry and explanations repeatable. Processing latency reflects actual machine timing and will vary.

The response contains metadata, per-observation telemetry and scores, one primary persistent event or `null`, and run metrics. The threshold baseline and Isolation Forest trained on the initial normal portion are combined with rolling features and a three-observation persistence rule. Risk and health scores are **prototype heuristic indicators, not failure probabilities**. An alert requests operator review; it does not establish a diagnosis.

## Planned extension

LSTM sequence modeling could be explored after representative labelled data and an evaluation protocol exist. It is not part of this MVP.
