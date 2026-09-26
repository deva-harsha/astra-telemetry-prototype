# Judge Q&A: model selection

## 1. Why did you test an LSTM?

**Short answer:** Sequence models can learn time-dependent normal behaviour, so we tested whether one improved detection on unseen telemetry.

**Deeper answer:** The LSTM Autoencoder used windows of 20 observations and was trained only on normal public training arrays. We compared it with frozen baselines on the same Phase 4 holdout and required it to pass a predeclared integration gate.

## 2. What is an LSTM Autoencoder in simple language?

**Short answer:** It compresses a short telemetry sequence and reconstructs it; poor reconstruction can indicate an unusual pattern.

**Deeper answer:** An LSTM encoder converts a sequence into a latent state, and an LSTM decoder reconstructs the input window. ASTRA uses reconstruction error as an anomaly score, followed by a frozen threshold and persistence rule.

## 3. How was it trained without anomaly labels?

**Short answer:** It learned normal patterns from public training arrays treated as normal under the dataset protocol.

**Deeper answer:** Training and validation windows came only from chronological splits of official training arrays. Public test labels were withheld until frozen holdout evaluation. Missing official training interval labels remain a limitation.

## 4. What is reconstruction error?

**Short answer:** It is the difference between the input sequence and the model's reconstruction.

**Deeper answer:** The experiment used mean squared error over each 20-observation window. High error indicates novelty relative to learned normal patterns; it is not proof of a fault.

## 5. Why did the LSTM fail?

**Short answer:** It failed the selection gate because event recall fell and median detection delay increased.

**Deeper answer:** Phase 4 event recall was 0.307692 versus 0.461538 for threshold, and median delay was 121 versus 64 observations. Macro F1 was also lower. Fewer false alerts did not compensate for missed and later events.

## 6. Why was it not integrated into the dashboard?

**Short answer:** The predeclared evidence gate failed, so integration would have ignored our own safety criteria.

**Deeper answer:** Macro F1 did not improve by 0.02 and event recall was lower. ASTRA keeps the experiment visible as research evidence while the live detector remains unchanged.

## 7. Does that mean deep learning is useless?

**Short answer:** No. This model and data setup did not justify live use.

**Deeper answer:** It reduced false alerts and passed practicality and cross-channel checks. Better mission data or other architectures may help, but they require the same leakage-safe evaluation.

## 8. Why can Isolation Forest outperform the LSTM?

**Short answer:** Simpler models can fit limited anonymized data better and need fewer assumptions.

**Deeper answer:** Isolation Forest detects sparse outliers in engineered features. The LSTM had one shared anonymized value, so extra sequence capacity did not guarantee useful signal.

## 9. Why are thresholds still valuable?

**Short answer:** They are transparent, fast and effective when operating limits are meaningful.

**Deeper answer:** Thresholds provide deterministic evidence and low complexity. Phase 1C retained robust thresholding because more complex combinations did not clear the frozen rule.

## 10. Why did the combined detector achieve the highest event recall?

**Short answer:** It flags events found by either component, increasing coverage at the cost of more false alerts.

**Deeper answer:** Phase 4 combined event recall was 0.615385, while false alerts rose to 4.141652 per 1,000 observations. That is a measured sensitivity versus alert-load trade-off.

## 11. Why not use GRU, Transformer or CNN next?

**Short answer:** Architecture shopping without better data would be weak science.

**Deeper answer:** The limits are anonymized single-value inputs, few labelled events and uncertain transfer. A next experiment needs mission data and a frozen hypothesis, not novelty.

## 12. Why was only value_0 used?

**Short answer:** It was the only consistently shared telemetry feature across selected SMAP and MSL channels.

**Deeper answer:** A pooled model needs comparable inputs. value_0 preserved one consistent feature without inventing semantics for channel-specific dimensions.

## 13. Why were command inputs excluded?

**Short answer:** Their meanings and dimensions vary across anonymized channels.

**Deeper answer:** Pooling them could let command structure identify channels rather than telemetry behaviour. Exclusion keeps the comparison reproducible.

## 14. How did you prevent data leakage?

**Short answer:** Selection used training and development data; holdout labels were opened only after configuration freeze.

**Deeper answer:** Chronological splits blocked future windows, scaling was train-fit, development channels were excluded from holdout selection, and the holdout runner refuses overwrite.

## 15. What is a frozen holdout?

**Short answer:** It is an unseen test set evaluated once after every model choice is locked.

**Deeper answer:** The manifest, model, scaling, threshold and gates are persisted before evaluation. Results cannot be tuned and still claimed as unseen.

## 16. Why are Phase 1C and Phase 4 numbers different?

**Short answer:** They used different frozen holdout channels and must not be compared directly.

**Deeper answer:** Phase 1C used 20 unseen channels. Phase 4 required channels unseen by earlier work and had nine valid channels. Only within-phase methods share a holdout.

## 17. What would be required before operational deployment?

**Short answer:** Mission-specific data, interfaces, limits, verification, security and operator qualification.

**Deeper answer:** It needs representative telemetry, calibrated costs, fault-management review, robust ingestion, time synchronization, audit storage, cybersecurity, human-factors testing and mission assurance.

## 18. What exactly is currently running in the live prototype?

**Short answer:** FastAPI batch simulation with fixed limits, Isolation Forest corroboration, trends and three-observation persistence.

**Deeper answer:** React replays 180 simulated observations from one API call. PyTorch, public data and the trained artifact are absent from production startup.

## 19. What is ASTRA's genuine technical contribution?

**Short answer:** A transparent workflow connecting persistent detection, evidence, event review and honest model selection.

**Deeper answer:** It combines deterministic simulation, hybrid detection, event grouping, attribution, operator state and reproducible offline evaluation. Its value is the auditable decision process.

## 20. What would you improve with mission-specific data?

**Short answer:** Calibrate signals, costs and timing to the actual subsystem and operator workflow.

**Deeper answer:** Use decoded physical channels, command context, mode labels, known limits, maintenance outcomes and anomaly intervals, then repeat frozen evaluation with operators.
