# ASTRA presentation claims

Use these claims exactly. ASTRA is a research prototype and judge-facing wording must preserve that boundary.

## Safe claims

- ASTRA includes a working simulated telemetry demonstration.
- ASTRA loaded all 81 public Telemanom SMAP/MSL channels.
- Robust threshold, Isolation Forest, combined detection and a PyTorch LSTM Autoencoder were evaluated offline.
- The LSTM was implemented in PyTorch and evaluated on a frozen holdout of nine unseen public telemetry channels.
- The LSTM was not selected because it reduced event recall and increased median detection delay on its Phase 4 holdout.
- ASTRA groups persistent events, shows supporting evidence, requests operator review and exports a labelled JSON event report.
- The live prototype uses fixed operating thresholds, Isolation Forest corroboration, trend checks and three-observation persistence on simulated telemetry.
- Deep learning was evaluated, not blindly deployed.

## Claims requiring qualification

| Claim | Required qualification |
|---|---|
| Early detection | "The prototype reports detection delay on labelled offline data; it does not predict failure time." |
| Reduced false alarms | "The Phase 4 LSTM produced fewer false alerts than the threshold and combined methods on the same nine-channel holdout, while missing more events." |
| Mission-wide | "The interface demonstrates multiple simulated subsystems; the public evaluation uses anonymized SMAP/MSL channels and is not mission-wide qualification." |
| Scalable | "The batch architecture and modular evaluation code are extensible; production scale has not been tested." |
| AI-powered | "The live demonstration includes scikit-learn Isolation Forest, while the PyTorch LSTM is offline research evidence only." |
| Public telemetry validation | "This is an offline research evaluation on anonymized Telemanom data with frozen splits, not operational validation." |
| Real time | "The browser progressively replays a completed 180-observation backend batch; there is no live spacecraft stream." |
| Explainable alert | "ASTRA shows deterministic contributing signals and detector evidence; it does not confirm root cause." |

## Prohibited claims

- Operationally validated
- Ready for spacecraft deployment
- Predicts spacecraft failures or exact failure time
- Confirms root cause
- LSTM improves ASTRA detection
- Connected to real-time spacecraft telemetry
- Controls a spacecraft
- Validated or endorsed by NASA, ESA or ISRO
- Production deep-learning detector
- Proven mission-safety performance
