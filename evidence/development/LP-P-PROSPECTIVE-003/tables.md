# Validation-only diagnostic results

Development records only. No test events are evaluated. Primary values use the fixed final epoch. Means ± sample SD describe the registered training seeds, not confidence intervals. Selected-checkpoint results remain separately labeled in the JSON summary.

## Final-epoch validation: all

| Dataset | Negatives | Scored / eligible | Training | Model | AP | AUC |
|---|---|---:|---|---|---:|---:|
| wikipedia | random | 300 / 300 | random | bounded-coupled | 0.9663 ± 0.0023 | 0.9563 ± 0.0031 |
| wikipedia | random | 300 / 300 | random | bounded-decoupled | 0.9689 ± 0.0058 | 0.9650 ± 0.0038 |
| wikipedia | random | 300 / 300 | random | tgn | 0.9047 ± 0.0075 | 0.9139 ± 0.0011 |
| wikipedia | random | 300 / 300 | mixed | bounded-coupled | 0.9547 ± 0.0040 | 0.9486 ± 0.0069 |
| wikipedia | random | 300 / 300 | mixed | bounded-decoupled | 0.9360 ± 0.0492 | 0.9506 ± 0.0156 |
| wikipedia | random | 300 / 300 | mixed | tgn | 0.8996 ± 0.0135 | 0.9083 ± 0.0133 |
| wikipedia | historical | 54 / 300 | random | bounded-coupled | 0.3524 ± 0.0297 | 0.1561 ± 0.0802 |
| wikipedia | historical | 54 / 300 | random | bounded-decoupled | 0.3338 ± 0.0046 | 0.1351 ± 0.0137 |
| wikipedia | historical | 54 / 300 | random | tgn | 0.7050 ± 0.0084 | 0.6377 ± 0.0147 |
| wikipedia | historical | 54 / 300 | mixed | bounded-coupled | 0.5690 ± 0.1162 | 0.4674 ± 0.0761 |
| wikipedia | historical | 54 / 300 | mixed | bounded-decoupled | 0.6717 ± 0.1317 | 0.6288 ± 0.0848 |
| wikipedia | historical | 54 / 300 | mixed | tgn | 0.6787 ± 0.0501 | 0.6310 ± 0.0444 |
| wikipedia | novel-pair | 300 / 300 | random | bounded-coupled | 0.9708 ± 0.0016 | 0.9611 ± 0.0026 |
| wikipedia | novel-pair | 300 / 300 | random | bounded-decoupled | 0.9768 ± 0.0023 | 0.9726 ± 0.0022 |
| wikipedia | novel-pair | 300 / 300 | random | tgn | 0.9225 ± 0.0039 | 0.9250 ± 0.0021 |
| wikipedia | novel-pair | 300 / 300 | mixed | bounded-coupled | 0.9666 ± 0.0036 | 0.9593 ± 0.0068 |
| wikipedia | novel-pair | 300 / 300 | mixed | bounded-decoupled | 0.9621 ± 0.0170 | 0.9636 ± 0.0070 |
| wikipedia | novel-pair | 300 / 300 | mixed | tgn | 0.9205 ± 0.0104 | 0.9203 ± 0.0096 |
| mooc | random | 300 / 300 | random | bounded-coupled | 0.8758 ± 0.0042 | 0.9152 ± 0.0066 |
| mooc | random | 300 / 300 | random | bounded-decoupled | 0.8763 ± 0.0139 | 0.9178 ± 0.0058 |
| mooc | random | 300 / 300 | random | tgn | 0.8736 ± 0.0069 | 0.9226 ± 0.0024 |
| mooc | random | 300 / 300 | mixed | bounded-coupled | 0.8108 ± 0.0097 | 0.8832 ± 0.0007 |
| mooc | random | 300 / 300 | mixed | bounded-decoupled | 0.8066 ± 0.0045 | 0.8811 ± 0.0025 |
| mooc | random | 300 / 300 | mixed | tgn | 0.8572 ± 0.0128 | 0.9043 ± 0.0060 |
| mooc | historical | 264 / 300 | random | bounded-coupled | 0.4690 ± 0.0630 | 0.4442 ± 0.0920 |
| mooc | historical | 264 / 300 | random | bounded-decoupled | 0.4253 ± 0.0178 | 0.3658 ± 0.0426 |
| mooc | historical | 264 / 300 | random | tgn | 0.3990 ± 0.0100 | 0.3434 ± 0.0193 |
| mooc | historical | 264 / 300 | mixed | bounded-coupled | 0.8596 ± 0.0029 | 0.8218 ± 0.0021 |
| mooc | historical | 264 / 300 | mixed | bounded-decoupled | 0.8697 ± 0.0053 | 0.8334 ± 0.0049 |
| mooc | historical | 264 / 300 | mixed | tgn | 0.6907 ± 0.0237 | 0.6889 ± 0.0353 |
| mooc | novel-pair | 300 / 300 | random | bounded-coupled | 0.9391 ± 0.0056 | 0.9586 ± 0.0066 |
| mooc | novel-pair | 300 / 300 | random | bounded-decoupled | 0.9387 ± 0.0164 | 0.9581 ± 0.0075 |
| mooc | novel-pair | 300 / 300 | random | tgn | 0.9498 ± 0.0085 | 0.9663 ± 0.0017 |
| mooc | novel-pair | 300 / 300 | mixed | bounded-coupled | 0.8749 ± 0.0114 | 0.9223 ± 0.0038 |
| mooc | novel-pair | 300 / 300 | mixed | bounded-decoupled | 0.8583 ± 0.0045 | 0.9156 ± 0.0024 |
| mooc | novel-pair | 300 / 300 | mixed | tgn | 0.8867 ± 0.0216 | 0.9309 ± 0.0092 |

## Final-epoch validation: inductive

| Dataset | Negatives | Scored / eligible | Training | Model | AP | AUC |
|---|---|---:|---|---|---:|---:|
| wikipedia | random | 171 / 171 | random | bounded-coupled | 0.9291 ± 0.0052 | 0.9109 ± 0.0050 |
| wikipedia | random | 171 / 171 | random | bounded-decoupled | 0.9270 ± 0.0121 | 0.9158 ± 0.0067 |
| wikipedia | random | 171 / 171 | random | tgn | 0.8282 ± 0.0143 | 0.8490 ± 0.0055 |
| wikipedia | random | 171 / 171 | mixed | bounded-coupled | 0.9050 ± 0.0146 | 0.8957 ± 0.0128 |
| wikipedia | random | 171 / 171 | mixed | bounded-decoupled | 0.8867 ± 0.0715 | 0.9007 ± 0.0216 |
| wikipedia | random | 171 / 171 | mixed | tgn | 0.8089 ± 0.0484 | 0.8417 ± 0.0324 |
| wikipedia | historical | 20 / 171 | random | bounded-coupled | 0.3396 ± 0.0343 | 0.0475 ± 0.0650 |
| wikipedia | historical | 20 / 171 | random | bounded-decoupled | 0.3230 ± 0.0025 | 0.0350 ± 0.0156 |
| wikipedia | historical | 20 / 171 | random | tgn | 0.5155 ± 0.0498 | 0.4083 ± 0.0216 |
| wikipedia | historical | 20 / 171 | mixed | bounded-coupled | 0.4842 ± 0.1071 | 0.2867 ± 0.0686 |
| wikipedia | historical | 20 / 171 | mixed | bounded-decoupled | 0.5563 ± 0.1488 | 0.4450 ± 0.1239 |
| wikipedia | historical | 20 / 171 | mixed | tgn | 0.4431 ± 0.0664 | 0.3083 ± 0.0960 |
| wikipedia | novel-pair | 171 / 171 | random | bounded-coupled | 0.9413 ± 0.0012 | 0.9230 ± 0.0024 |
| wikipedia | novel-pair | 171 / 171 | random | bounded-decoupled | 0.9467 ± 0.0050 | 0.9358 ± 0.0052 |
| wikipedia | novel-pair | 171 / 171 | random | tgn | 0.8678 ± 0.0072 | 0.8789 ± 0.0056 |
| wikipedia | novel-pair | 171 / 171 | mixed | bounded-coupled | 0.9328 ± 0.0082 | 0.9197 ± 0.0103 |
| wikipedia | novel-pair | 171 / 171 | mixed | bounded-decoupled | 0.9286 ± 0.0257 | 0.9270 ± 0.0079 |
| wikipedia | novel-pair | 171 / 171 | mixed | tgn | 0.8624 ± 0.0152 | 0.8709 ± 0.0196 |
| mooc | random | 144 / 144 | random | bounded-coupled | 0.9053 ± 0.0065 | 0.9352 ± 0.0042 |
| mooc | random | 144 / 144 | random | bounded-decoupled | 0.9229 ± 0.0085 | 0.9426 ± 0.0049 |
| mooc | random | 144 / 144 | random | tgn | 0.9291 ± 0.0032 | 0.9558 ± 0.0017 |
| mooc | random | 144 / 144 | mixed | bounded-coupled | 0.8429 ± 0.0013 | 0.9024 ± 0.0027 |
| mooc | random | 144 / 144 | mixed | bounded-decoupled | 0.8501 ± 0.0094 | 0.9036 ± 0.0012 |
| mooc | random | 144 / 144 | mixed | tgn | 0.8703 ± 0.0229 | 0.9069 ± 0.0179 |
| mooc | historical | 108 / 144 | random | bounded-coupled | 0.4522 ± 0.0555 | 0.4330 ± 0.1039 |
| mooc | historical | 108 / 144 | random | bounded-decoupled | 0.3967 ± 0.0427 | 0.2730 ± 0.0591 |
| mooc | historical | 108 / 144 | random | tgn | 0.4132 ± 0.0229 | 0.3487 ± 0.0542 |
| mooc | historical | 108 / 144 | mixed | bounded-coupled | 0.8890 ± 0.0037 | 0.8492 ± 0.0060 |
| mooc | historical | 108 / 144 | mixed | bounded-decoupled | 0.9002 ± 0.0028 | 0.8643 ± 0.0083 |
| mooc | historical | 108 / 144 | mixed | tgn | 0.7526 ± 0.0172 | 0.7280 ± 0.0229 |
| mooc | novel-pair | 144 / 144 | random | bounded-coupled | 0.9369 ± 0.0018 | 0.9523 ± 0.0020 |
| mooc | novel-pair | 144 / 144 | random | bounded-decoupled | 0.9341 ± 0.0126 | 0.9483 ± 0.0068 |
| mooc | novel-pair | 144 / 144 | random | tgn | 0.9541 ± 0.0251 | 0.9683 ± 0.0132 |
| mooc | novel-pair | 144 / 144 | mixed | bounded-coupled | 0.8696 ± 0.0180 | 0.9163 ± 0.0042 |
| mooc | novel-pair | 144 / 144 | mixed | bounded-decoupled | 0.8392 ± 0.0228 | 0.9052 ± 0.0059 |
| mooc | novel-pair | 144 / 144 | mixed | tgn | 0.8789 ± 0.0297 | 0.9136 ± 0.0188 |

## Paired routing and sampling interaction

Routing is decoupled minus coupled; interaction is mixed routing minus random routing. Values are AP percentage points, paired within seed. The interaction does not by itself show that either model improves in absolute terms.

| Dataset | Negatives | Cohort | Random routing Δ | Mixed routing Δ | Interaction | Interaction by seed |
|---|---|---|---:|---:|---:|---|
| wikipedia | random | all | 0.2572 ± 0.5517 | -1.8719 ± 4.7933 | -2.1291 ± 4.3088 | -0.1954, -7.0660, 0.8741 |
| wikipedia | random | inductive | -0.2074 ± 1.3065 | -1.8245 ± 6.4566 | -1.6171 ± 5.3584 | -0.2062, -7.5398, 2.8946 |
| wikipedia | historical | all | -1.8580 ± 2.5187 | 10.2674 ± 1.5601 | 12.1253 ± 3.4815 | 9.4205, 16.0534, 10.9020 |
| wikipedia | historical | inductive | -1.6538 ± 3.1909 | 7.2125 ± 5.4059 | 8.8662 ± 8.5895 | 4.1527, 18.7806, 3.6654 |
| wikipedia | novel-pair | all | 0.6081 ± 0.2150 | -0.4462 ± 1.6418 | -1.0543 ± 1.6133 | -0.6420, -2.8338, 0.3128 |
| wikipedia | novel-pair | inductive | 0.5413 ± 0.4695 | -0.4233 ± 2.2351 | -0.9646 ± 2.0409 | -0.8034, -3.0813, 0.9909 |
| mooc | random | all | 0.0526 ± 1.5132 | -0.4137 ± 1.2444 | -0.4663 ± 2.2384 | -3.0240, 1.1352, 0.4899 |
| mooc | random | inductive | 1.7680 ± 1.4924 | 0.7272 ± 1.0603 | -1.0408 ± 2.4432 | -3.8204, -0.0685, 0.7666 |
| mooc | historical | all | -4.3698 ± 6.3314 | 1.0055 ± 0.4681 | 5.3753 ± 6.5921 | 5.6844, -1.3659, 11.8074 |
| mooc | historical | inductive | -5.5492 ± 9.7212 | 1.1171 ± 0.6293 | 6.6663 ± 10.0125 | 12.8950, -4.8833, 11.9873 |
| mooc | novel-pair | all | -0.0406 ± 1.8914 | -1.6641 ± 1.2182 | -1.6236 ± 0.7928 | -2.4914, -1.4420, -0.9373 |
| mooc | novel-pair | inductive | -0.2874 ± 1.4397 | -3.0422 ± 4.0152 | -2.7547 ± 2.5930 | -3.0424, -0.0299, -5.1919 |

## Final-epoch shared-transformation gradient probes

Norms are means over the registered probes pooled across training seeds. The negative-cosine fraction uses only probes with both norms nonzero. These are descriptive accumulation increments, with floating-point subtraction limits; no causal interpretation or independent-sample inference is made.

| Dataset | Training | Model | Module | Mean prediction norm | Mean auxiliary increment norm | Defined cosine probes | Negative cosine fraction |
|---|---|---|---|---:|---:|---:|---:|
| wikipedia | random | bounded-coupled | csn | 0.0177158 | 6.72297e-05 | 65 / 66 | 0.4000 |
| wikipedia | random | bounded-coupled | context | 0.00442943 | 0 | 0 / 66 | undefined |
| wikipedia | random | bounded-coupled | drgc | 46.1123 | 5.60338e-28 | 66 / 66 | 0.0000 |
| wikipedia | random | bounded-decoupled | csn | 0 | 4.4892e-05 | 0 / 66 | undefined |
| wikipedia | random | bounded-decoupled | context | 0 | 0 | 0 / 66 | undefined |
| wikipedia | random | bounded-decoupled | drgc | 0 | 4.60558e-28 | 0 / 66 | undefined |
| wikipedia | mixed | bounded-coupled | csn | 0.0158945 | 0.000131375 | 65 / 66 | 0.4923 |
| wikipedia | mixed | bounded-coupled | context | 0.00636837 | 0 | 0 / 66 | undefined |
| wikipedia | mixed | bounded-coupled | drgc | 27.8744 | 5.12933e-28 | 66 / 66 | 0.0000 |
| wikipedia | mixed | bounded-decoupled | csn | 0 | 4.4892e-05 | 0 / 66 | undefined |
| wikipedia | mixed | bounded-decoupled | context | 0 | 0 | 0 / 66 | undefined |
| wikipedia | mixed | bounded-decoupled | drgc | 0 | 4.60558e-28 | 0 / 66 | undefined |
| mooc | random | bounded-coupled | csn | 0.016667 | 3.78892e-05 | 60 / 60 | 0.3833 |
| mooc | random | bounded-coupled | context | 0.0515148 | 0 | 0 / 60 | undefined |
| mooc | random | bounded-coupled | drgc | 199.066 | 2.68969e-24 | 60 / 60 | 0.0000 |
| mooc | random | bounded-decoupled | csn | 0 | 2.56971e-05 | 0 / 60 | undefined |
| mooc | random | bounded-decoupled | context | 0 | 0 | 0 / 60 | undefined |
| mooc | random | bounded-decoupled | drgc | 0 | 2.31583e-24 | 0 / 60 | undefined |
| mooc | mixed | bounded-coupled | csn | 0.020099 | 4.49115e-05 | 60 / 60 | 0.3667 |
| mooc | mixed | bounded-coupled | context | 0.169585 | 0 | 0 / 60 | undefined |
| mooc | mixed | bounded-coupled | drgc | 223.483 | 2.4912e-24 | 60 / 60 | 0.0000 |
| mooc | mixed | bounded-decoupled | csn | 0 | 2.56971e-05 | 0 / 60 | undefined |
| mooc | mixed | bounded-decoupled | context | 0 | 0 | 0 / 60 | undefined |
| mooc | mixed | bounded-decoupled | drgc | 0 | 2.31583e-24 | 0 / 60 | undefined |

## Decoder movement and sensitivity

Each row is a trained cell. These measurements describe the unchanged bounded initialization; they do not test an alternative initialization or prove saturation caused poor ranking.

| Dataset | Training | Model | Seed | Max absolute log-odds displacement | Min final sigmoid slope | Max decoder gradient RMS |
|---|---|---|---:|---:|---:|---:|
| wikipedia | random | bounded-coupled | 1 | 2.00247 | 7.51013e-06 | 0.0738494 |
| wikipedia | random | bounded-decoupled | 1 | 2.00193 | 7.51013e-06 | 0.0541384 |
| wikipedia | mixed | bounded-coupled | 1 | 2.00164 | 7.51013e-06 | 0.0584898 |
| wikipedia | mixed | bounded-decoupled | 1 | 2.00082 | 7.51013e-06 | 0.0508478 |
| wikipedia | random | bounded-coupled | 2 | 2.00359 | 7.51013e-06 | 0.072529 |
| wikipedia | random | bounded-decoupled | 2 | 2.00198 | 7.51013e-06 | 0.0552194 |
| wikipedia | mixed | bounded-coupled | 2 | 2.00171 | 7.51013e-06 | 0.0747716 |
| wikipedia | mixed | bounded-decoupled | 2 | 1.9998 | 7.51013e-06 | 0.0544421 |
| wikipedia | random | bounded-coupled | 3 | 2.00214 | 7.51013e-06 | 0.06651 |
| wikipedia | random | bounded-decoupled | 3 | 2.0021 | 7.51013e-06 | 0.0585523 |
| wikipedia | mixed | bounded-coupled | 3 | 2.00184 | 7.51013e-06 | 0.0795567 |
| wikipedia | mixed | bounded-decoupled | 3 | 1.99988 | 7.51013e-06 | 0.0568099 |
| mooc | random | bounded-coupled | 1 | 1.81816 | 6.07964e-06 | 0.0557897 |
| mooc | random | bounded-decoupled | 1 | 1.81805 | 3.93389e-06 | 0.0319106 |
| mooc | mixed | bounded-coupled | 1 | 1.81913 | 6.19884e-06 | 0.0475842 |
| mooc | mixed | bounded-decoupled | 1 | 1.81894 | 6.19884e-06 | 0.0266548 |
| mooc | random | bounded-coupled | 2 | 1.81855 | 6.19884e-06 | 0.0520105 |
| mooc | random | bounded-decoupled | 2 | 1.81874 | 6.19884e-06 | 0.0305619 |
| mooc | mixed | bounded-coupled | 2 | 1.81914 | 6.19884e-06 | 0.0432283 |
| mooc | mixed | bounded-decoupled | 2 | 1.81898 | 6.19884e-06 | 0.0291297 |
| mooc | random | bounded-coupled | 3 | 1.81794 | 6.19884e-06 | 0.0618723 |
| mooc | random | bounded-decoupled | 3 | 1.81856 | 6.19884e-06 | 0.033504 |
| mooc | mixed | bounded-coupled | 3 | 1.81905 | 6.19884e-06 | 0.0328576 |
| mooc | mixed | bounded-decoupled | 3 | 1.81906 | 6.19884e-06 | 0.0285345 |

## Deterministic controls

Repeated/new-positive and shared-support controls are also available in the summary.

| Dataset | Negatives | Cohort | Control | AP | AUC |
|---|---|---|---|---:|---:|
| wikipedia | random | all | recency | 0.9088 | 0.8667 |
| wikipedia | random | all | recurrence | 0.8583 | 0.8583 |
| wikipedia | random | inductive | recency | 0.8573 | 0.8034 |
| wikipedia | random | inductive | recurrence | 0.7719 | 0.7719 |
| wikipedia | historical | all | recency | 0.6624 | 0.5031 |
| wikipedia | historical | all | recurrence | 0.4285 | 0.3148 |
| wikipedia | historical | inductive | recency | 0.5908 | 0.3400 |
| wikipedia | historical | inductive | recurrence | 0.4157 | 0.1750 |
| wikipedia | novel-pair | all | recency | 0.9088 | 0.8667 |
| wikipedia | novel-pair | all | recurrence | 0.8583 | 0.8583 |
| wikipedia | novel-pair | inductive | recency | 0.8573 | 0.8034 |
| wikipedia | novel-pair | inductive | recurrence | 0.7719 | 0.7719 |
| mooc | random | all | recency | 0.7589 | 0.6982 |
| mooc | random | all | recurrence | 0.6653 | 0.6900 |
| mooc | random | inductive | recency | 0.7155 | 0.6479 |
| mooc | random | inductive | recurrence | 0.6386 | 0.6528 |
| mooc | historical | all | recency | 0.3908 | 0.2710 |
| mooc | historical | all | recurrence | 0.4154 | 0.2367 |
| mooc | historical | inductive | recency | 0.3528 | 0.1898 |
| mooc | historical | inductive | recurrence | 0.4149 | 0.1852 |
| mooc | novel-pair | all | recency | 0.7806 | 0.7136 |
| mooc | novel-pair | all | recurrence | 0.7073 | 0.7150 |
| mooc | novel-pair | inductive | recency | 0.7275 | 0.6554 |
| mooc | novel-pair | inductive | recurrence | 0.6445 | 0.6562 |
