# ASTRA recorded telemetry import format

## Scope

ASTRA imports recorded CSV files for local-session preview and replay. A file reaches the existing detector only when it satisfies the complete `astra-sim-v1@1.0` prototype profile. Other valid time-series files remain visualisation-only.

Import compatibility is a software contract, not spacecraft certification or operational validation. Uploaded content is sent only to the configured ASTRA backend, held in memory during the request and never permanently stored.

## Resource limits

- File extension and content type: CSV only
- Encoding: UTF-8 or UTF-8 with BOM
- Maximum file size: 10 MB
- Maximum data rows: 50,000
- Preview: first 10 rows
- Header names must be present and unique
- At least one usable numeric telemetry column is required

## Supported structure

The timestamp and mission identifier columns may be selected in the mapping interface. The recommended names are:

| Column | Requirement | Meaning |
|---|---|---|
| `timestamp` | Required | An ISO 8601 timestamp parseable with a UTC offset or `Z` |
| `mission_id` | Optional | A display identifier, limited to the first non-empty value |
| Canonical telemetry columns | Required for detector compatibility | Numeric values in the units below |

The downloadable template uses this header:

```csv
timestamp,mission_id,battery_voltage,battery_current,battery_temperature,signal_strength,attitude_error,payload_temperature,propulsion_pressure,radiation_level
```

## Canonical channels and units

| Canonical channel | Required unit |
|---|---|
| `battery_voltage` | V |
| `battery_current` | A |
| `battery_temperature` | degrees Celsius |
| `signal_strength` | dBm |
| `attitude_error` | degrees |
| `payload_temperature` | degrees Celsius |
| `propulsion_pressure` | kPa |
| `radiation_level` | mGy/h |

All eight channels are required for `astra-sim-v1` detector compatibility. The operator must explicitly confirm the source values use these units. This confirmation does not prove calibration or mission suitability.

## Compatibility levels

### Compatible for prototype analysis

- Every canonical channel is mapped exactly once.
- Every timestamp is valid, chronological and unique.
- Sampling is continuous under the inferred interval.
- Required values are numeric, finite and complete.
- Values remain inside broad profile sanity bounds.
- Required prototype units are explicitly confirmed.

The file may be passed through the existing fixed-threshold, Isolation Forest, trend and three-observation persistence workflow.

### Visualisation only

The file is a valid timestamped numeric series but does not satisfy the full profile. ASTRA allows replay and quality inspection while suppressing detector events, risk scores and health scores.

> Detection disabled because this dataset does not match a validated ASTRA prototype profile.

### Invalid

Replay is blocked when the file cannot be interpreted safely, including empty files, malformed or duplicate headers, unusable timestamps, missing numeric telemetry, excess size or excess rows.

## Data-quality rules

ASTRA reports:

- Missing or non-numeric values
- Duplicate timestamps
- Out-of-order timestamps
- Estimated gaps relative to the median positive interval
- Constant or nearly constant numeric channels
- Formula-like cell text
- Mapped values outside broad prototype bounds

Warnings are not anomalies. They may prevent detector compatibility when they violate the supported profile.

## Security boundaries

- Uploaded filenames are reduced to a bounded display-only leaf name.
- File paths are never built from uploaded names.
- Formula-like cells are treated as non-numeric text and are never executed.
- Preview values are rendered as text by React, never interpreted as HTML.
- Complete telemetry is not written to logs, event exports or investigation reports.
- SHA-256 is recorded as provenance evidence, not proof of authenticity or safety.
- Files are not permanently stored.
- No upload is sent to a third-party service.

## Example

Download `/examples/astra-compatible-template.csv` from the frontend. Two labelled ASTRA-generated demonstration datasets are also provided:

- `astra-normal-demo.csv`
- `astra-power-fault-demo.csv`

## Current limitations

- Only `astra-sim-v1@1.0` is detector compatible.
- Unit confirmation is operator supplied; ASTRA cannot infer physical units from arbitrary values.
- Broad sanity bounds do not establish sensor calibration.
- Imported data is batch processed and replayed in the browser.
- No mission-specific command context, mode context or time synchronization is implemented.
- Compatibility does not imply operational readiness.

The importer additionally limits files to 64 columns. Compatible analysis requires at least five observations with every timestamp step equal to 60 seconds. The unchanged detector trains on the first 60% of the uploaded file, assumed to represent normal telemetry; ASTRA cannot verify that reference assumption. Uploaded numeric values are preserved in the response. The three-row template demonstrates format and remains visualisation-only until extended to a sufficient recorded sequence.
