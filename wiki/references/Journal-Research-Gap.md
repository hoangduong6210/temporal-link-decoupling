---
title: Journal Research Gap and Literature Review Boundary
status: focused primary-source screening; novelty assessment incomplete
last_updated: 2026-10-03
paper_source: false
---

# Journal Research Gap and Literature Review Boundary

The working research question is when a prediction-gradient boundary helps a
stateful temporal link predictor under different training and evaluation
negative regimes. The [diagnostic review](../evidence/Prospective-Diagnostics.md)
supports investigating that conditional question. It does not establish a
novel mechanism, a superior architecture or a publication-ready contribution.

## Primary sources screened

| Source | Material reviewed | Consequence for this project | Work still open |
|---|---|---|---|
| [Towards Better Evaluation for Dynamic Link Prediction](https://proceedings.neurips.cc/paper_files/paper/2022/hash/d49042a5d49818711c401d34172f9900-Abstract-Datasets_and_Benchmarks.html) | Primary abstract and authors' implementation | Recurrence and challenging negatives are established evaluation concerns; discovering random-negative optimism is insufficient novelty | Compare exact sampler support and protocols; the project's source-specific history and skipped rows do not reproduce the external benchmark |
| [Towards Better Dynamic Graph Learning: New Architecture and Unified Library](https://proceedings.neurips.cc/paper_files/paper/2023/file/d611019afba70d547bd595e8a4158f55-Paper-Conference.pdf) and [DyGLib](https://github.com/yule-BUAA/DyGLib) | Abstract and introduction | DyGFormer uses interaction histories, neighbor co-occurrence and patching; the library is a candidate source of stronger comparisons | Full method review, pinned original implementation, feature/candidate parity and compute budget before comparator admission |
| [Temporal Graph Benchmark for Machine Learning on Temporal Graphs](https://proceedings.neurips.cc/paper_files/paper/2023/hash/066b98e63313162f6562b35962671288-Abstract.html) | Primary abstract | Diverse datasets and explicit evaluation contracts matter | Choose an appropriate independent stream; sampled binary AP/AUC must not imply reproduction of a different ranking benchmark |
| [Gradient Surgery for Multi-Task Learning](https://proceedings.neurips.cc/paper/2020/file/3fe78a8acf5fda99de95303940a2420c-Paper.pdf) | Abstract and introduction | Gradient interference depends on more than a negative cosine; adaptive gradient handling has substantial prior work | Review relevant gradient-routing and auxiliary-learning literature before claiming a new intervention; reconcile Adam and sequential state updates |
| [Future Link Prediction Without Memory or Aggregation](https://proceedings.neurips.cc/paper_files/paper/2025/file/036912a83bdbb1fd792baf6532f102d8-Paper-Conference.pdf) | Abstract, problem statement and method | CRAFT uses learned node identities and target-aware cross-attention and distinguishes repeated from unseen edges | Unseen edges are not unseen nodes; audit negative-sampling exposure to future catalogue identities before any inductive comparison. No implementation has been fetched or validated |

This is focused screening, not an exhaustive survey. Each row names the actual
review boundary. Numerical claims and theorem statements from unread sections
must not enter the manuscript. Complete bibliographic metadata, implementation
licenses and protocol parity remain prerequisites for admission.

## Contribution test

A defensible contribution would connect an explicitly specified routing
intervention to reproducible conditions under which it helps or harms, while
separating sampling effects, auxiliary learning and fixed-backbone behavior.
The existing diagnostics motivate that study but cannot replace it.

An event-occurrence target and a latent edge-existence readout may encode
different assumptions. This is a model-specification hypothesis requiring a
registered head control, not an explanation established by the current scores.
Likewise, near-boundary probabilities alone do not prove ineffective learning.

Before full execution, review the closest routing and stateful-learning work,
state the precise distinction being tested, and define falsifying outcomes.
If matched controls explain the apparent detachment advantage without a new
mechanism, report that result and revise the contribution accordingly. Journal
quartile does not settle the novelty question.
