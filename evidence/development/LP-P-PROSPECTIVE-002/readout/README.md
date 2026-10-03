# Saved-checkpoint readout diagnosis

Technical development evidence only; no publication claim is admitted.
The [canonical development contract](../../../../wiki/methods/Prospective-Development.md)
owns interpretation and the next experiment.

Job `7648211` replayed the original pilot checkpoints from source `e6dd4e7`.
Checkpoint/report hashes are recorded in `diagnosis.json`. All saved test logits
were reproduced exactly after restoring the recorded PyTorch thread count.
`slurm-accounting.tsv` retains native terminal outcomes; `checksums.sha256`
covers both the successful and earlier failed report.

The earlier job `7648208` used a different thread count and failed its strict
replay check at an absolute logit difference of approximately 0.0000553.
The retry matched the recorded thread count rather than loosening the check.
That failed attempt remains in `failed-replay.json`.

On Wikipedia historical negatives, upper clipping occurs in 29 / 41 coupled
negative scores and 41 / 41 detached negative scores. Corresponding positive
counts are 7 / 41 and 29 / 41. The detached negative logits therefore all tie.
Some learned mixture weights exceed one. Ranking the unclipped mixture raises
detached historical AUC from 0.3537 to 0.4557, while coupled AUC decreases from
0.2246 to 0.1939. Unclipped values are not valid probabilities or retrained
results and are not proposed as a corrected benchmark.

Neither MOOC arm clips its historical scores, yet its ranking remains poor.
Clipping thus explains a numerical defect in part of this pilot, not the full
historical-negative failure or a general mechanism of gradient decoupling.

The bounded readout intervention and original-module TGN comparator are
registered separately in `protocols/prospective_development_v2.toml`.
