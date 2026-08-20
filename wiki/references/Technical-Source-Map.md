---
title: Technical Source Map
status: migration reference map
last_updated: 2026-08-19
paper_source: false
---

# Technical Source Map

The manuscript bibliography is not a verified citation registry. UNKNOWN means
that no exact primary source has yet been admitted to the canonical wiki.

| Topic/source owner | Intended use | Primary source identity | Verification state | Admission boundary |
|---|---|---|---|---|
| Wikipedia and MOOC raw streams | Dataset provenance and acquisition | Intended JODIE/SNAP sources named in builder code; exact files UNKNOWN | BLOCKED: raw digest, acquisition date, license, and citation are absent | No dataset release or external benchmark claim |
| CoEdit construction | Population, event definition, exclusions, and units | `experiments/dataset_builders/build_coedit.py`; upstream input UNKNOWN | BLOCKED pending code/provenance audit | No source-independence claim |
| Average precision | Endpoint definition | Exact primary metric source UNKNOWN | BLOCKED pending definition and implementation parity review | No quantitative claim |
| Random/historical/inductive negatives | Evaluation protocol | Citations exist only in quarantined working manuscript | BLOCKED pending primary-source and implementation verification | Regimes must not be mixed |
| Temporal baseline families | Comparator scope and parity | Citations exist only in quarantined working manuscript | BLOCKED pending primary-source and official-implementation review | No SOTA or protocol-parity claim |
| Stop-gradient/frozen probing | Method positioning | Citations exist only in quarantined working manuscript | BLOCKED pending primary-source verification | No novelty or generalization claim |

Before any claim admission, record exact title/authors/venue/DOI or stable URL,
the date checked, the proposition supported, and the reviewer decision here.
