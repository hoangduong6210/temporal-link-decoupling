# Development results — not admitted publication evidence

Derived from `matrix/summary.json`. Entries are means ± sample standard deviations across the registered training seeds; these are descriptive quantities, not confidence intervals or significance tests.

## Test cohort before inductive filtering

| Dataset | Negatives | Scored / eligible | Model | AP | AUC |
|---|---|---:|---|---:|---:|
| wikipedia | random | 300 / 300 | legacy-coupled | 0.9840 ± 0.0007 | 0.9805 ± 0.0011 |
| wikipedia | random | 300 / 300 | legacy-decoupled | 0.9844 ± 0.0002 | 0.9810 ± 0.0004 |
| wikipedia | random | 300 / 300 | bounded-coupled | 0.9841 ± 0.0006 | 0.9807 ± 0.0008 |
| wikipedia | random | 300 / 300 | bounded-decoupled | 0.9845 ± 0.0001 | 0.9813 ± 0.0003 |
| wikipedia | random | 300 / 300 | tgn | 0.9472 ± 0.0037 | 0.9512 ± 0.0033 |
| wikipedia | historical | 41 / 300 | legacy-coupled | 0.3926 ± 0.0607 | 0.2629 ± 0.1538 |
| wikipedia | historical | 41 / 300 | legacy-decoupled | 0.4404 ± 0.0123 | 0.3724 ± 0.0189 |
| wikipedia | historical | 41 / 300 | bounded-coupled | 0.3388 ± 0.0173 | 0.1416 ± 0.0724 |
| wikipedia | historical | 41 / 300 | bounded-decoupled | 0.3611 ± 0.0123 | 0.2193 ± 0.0313 |
| wikipedia | historical | 41 / 300 | tgn | 0.8180 ± 0.0446 | 0.7914 ± 0.0290 |
| wikipedia | novel-pair | 300 / 300 | legacy-coupled | 0.9844 ± 0.0007 | 0.9809 ± 0.0011 |
| wikipedia | novel-pair | 300 / 300 | legacy-decoupled | 0.9850 ± 0.0006 | 0.9817 ± 0.0007 |
| wikipedia | novel-pair | 300 / 300 | bounded-coupled | 0.9843 ± 0.0004 | 0.9809 ± 0.0007 |
| wikipedia | novel-pair | 300 / 300 | bounded-decoupled | 0.9851 ± 0.0005 | 0.9820 ± 0.0005 |
| wikipedia | novel-pair | 300 / 300 | tgn | 0.9558 ± 0.0021 | 0.9571 ± 0.0017 |
| mooc | random | 301 / 301 | legacy-coupled | 0.8920 ± 0.0048 | 0.9264 ± 0.0022 |
| mooc | random | 301 / 301 | legacy-decoupled | 0.8869 ± 0.0080 | 0.9260 ± 0.0033 |
| mooc | random | 301 / 301 | bounded-coupled | 0.8769 ± 0.0119 | 0.9167 ± 0.0104 |
| mooc | random | 301 / 301 | bounded-decoupled | 0.8940 ± 0.0105 | 0.9282 ± 0.0054 |
| mooc | random | 301 / 301 | tgn | 0.8919 ± 0.0021 | 0.9319 ± 0.0025 |
| mooc | historical | 261 / 301 | legacy-coupled | 0.3728 ± 0.0117 | 0.2621 ± 0.0267 |
| mooc | historical | 261 / 301 | legacy-decoupled | 0.4074 ± 0.0208 | 0.3592 ± 0.0541 |
| mooc | historical | 261 / 301 | bounded-coupled | 0.4660 ± 0.0719 | 0.4372 ± 0.1187 |
| mooc | historical | 261 / 301 | bounded-decoupled | 0.4041 ± 0.0277 | 0.3489 ± 0.0602 |
| mooc | historical | 261 / 301 | tgn | 0.3909 ± 0.0174 | 0.3280 ± 0.0233 |
| mooc | novel-pair | 301 / 301 | legacy-coupled | 0.9297 ± 0.0063 | 0.9563 ± 0.0014 |
| mooc | novel-pair | 301 / 301 | legacy-decoupled | 0.9433 ± 0.0084 | 0.9584 ± 0.0034 |
| mooc | novel-pair | 301 / 301 | bounded-coupled | 0.9283 ± 0.0047 | 0.9510 ± 0.0057 |
| mooc | novel-pair | 301 / 301 | bounded-decoupled | 0.9440 ± 0.0101 | 0.9605 ± 0.0040 |
| mooc | novel-pair | 301 / 301 | tgn | 0.9466 ± 0.0067 | 0.9597 ± 0.0047 |

## Paired inductive AP differences

Decoupled minus coupled, in percentage points. Seed order is the registered order. Negative values are retained.

| Dataset | Negatives | Decoder | Mean ± sample SD (pp) | Per-seed differences (pp) |
|---|---|---|---:|---|
| wikipedia | random | legacy | 0.1845 ± 0.1182 | 0.2257, 0.0512, 0.2767 |
| wikipedia | random | bounded | 0.1535 ± 0.2576 | -0.0067, 0.0165, 0.4506 |
| wikipedia | historical | legacy | 0.0000 ± 0.0000 | 0.0000, 0.0000, 0.0000 |
| wikipedia | historical | bounded | 1.8353 ± 3.1789 | 0.0000, 5.5060, 0.0000 |
| wikipedia | novel-pair | legacy | 0.2014 ± 0.0873 | 0.1956, 0.2914, 0.1171 |
| wikipedia | novel-pair | bounded | 0.2880 ± 0.2439 | 0.2475, 0.5497, 0.0669 |
| mooc | random | legacy | -2.6582 ± 1.9655 | -0.6528, -2.7406, -4.5812 |
| mooc | random | bounded | 2.5079 ± 1.8357 | 0.6482, 4.3186, 2.5570 |
| mooc | historical | legacy | -0.0951 ± 1.0049 | -0.5548, 1.0575, -0.7879 |
| mooc | historical | bounded | -7.9094 ± 6.0951 | -11.0433, -0.8850, -11.7999 |
| mooc | novel-pair | legacy | 0.1659 ± 2.4550 | 2.7933, -2.0697, -0.2258 |
| mooc | novel-pair | bounded | 2.0805 ± 2.6681 | 2.8233, -0.8803, 4.2986 |

## Deterministic history controls

Controls use the same candidates and metric rows. See the summary for repeated/new positive and shared-support cohorts.

| Dataset | Negatives | Cohort | Scored / eligible | Control | AP | AUC |
|---|---|---|---:|---|---:|---:|
| wikipedia | random | all | 300 / 300 | recurrence | 0.9083 | 0.9083 |
| wikipedia | random | all | 300 / 300 | recency | 0.9448 | 0.9166 |
| wikipedia | random | repeated-positive | 245 / 245 | recurrence | 1.0000 | 1.0000 |
| wikipedia | random | repeated-positive | 245 / 245 | recency | 1.0000 | 1.0000 |
| wikipedia | random | new-pair-positive | 55 / 55 | recurrence | 0.5000 | 0.5000 |
| wikipedia | random | new-pair-positive | 55 / 55 | recency | 0.5000 | 0.5000 |
| wikipedia | historical | all | 41 / 300 | recurrence | 0.4394 | 0.3537 |
| wikipedia | historical | all | 41 / 300 | recency | 0.7838 | 0.6526 |
| wikipedia | historical | repeated-positive | 29 / 245 | recurrence | 0.5000 | 0.5000 |
| wikipedia | historical | repeated-positive | 29 / 245 | recency | 0.9613 | 0.9501 |
| wikipedia | historical | new-pair-positive | 12 / 55 | recurrence | 0.5000 | 0.0000 |
| wikipedia | historical | new-pair-positive | 12 / 55 | recency | 0.3273 | 0.0000 |
| mooc | random | all | 301 / 301 | recurrence | 0.6363 | 0.6561 |
| mooc | random | all | 301 / 301 | recency | 0.7154 | 0.6552 |
| mooc | random | repeated-positive | 110 / 110 | recurrence | 0.9402 | 0.9682 |
| mooc | random | repeated-positive | 110 / 110 | recency | 0.9828 | 0.9831 |
| mooc | random | new-pair-positive | 191 / 191 | recurrence | 0.5000 | 0.4764 |
| mooc | random | new-pair-positive | 191 / 191 | recency | 0.4644 | 0.4693 |
| mooc | historical | all | 261 / 301 | recurrence | 0.4145 | 0.1935 |
| mooc | historical | all | 261 / 301 | recency | 0.3754 | 0.2356 |
| mooc | historical | repeated-positive | 101 / 110 | recurrence | 0.5000 | 0.5000 |
| mooc | historical | repeated-positive | 101 / 110 | recency | 0.5800 | 0.6213 |
| mooc | historical | new-pair-positive | 160 / 191 | recurrence | 0.5000 | 0.0000 |
| mooc | historical | new-pair-positive | 160 / 191 | recency | 0.3088 | 0.0000 |
