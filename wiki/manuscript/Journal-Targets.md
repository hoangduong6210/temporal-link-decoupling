---
title: Journal Targets
status: JIIS selected; fallback venues retained
last_updated: 2026-10-02
paper_source: false
---

# Journal Targets

The active order is **JIIS → KAIS → IJMLC**, as selected in
[the venue decision](../decisions/0002-journal-target-order.md). Exact page,
abstract and keyword limits are publisher metadata in the
[venue register](journal-targets.toml). Instructions were checked on 2026-10-02;
recheck them when assembling the submission. Venue metadata is separate from
the experimental values owned by the [claim registry](../claims/Current-Claim-Language.md).

## Fit and adaptation

The editorial positioning below is our interpretation of publisher scopes,
not a promise of acceptance or a ranking by difficulty.

| Venue | Role and proposed emphasis | Work when preparing or switching |
|---|---|---|
| [JIIS](https://link.springer.com/journal/10844/aims-and-scope) | Primary: temporal information-system design, event history, gradient routing and interpreted evaluation | Connect the model to a concrete interaction-data problem; explain state and scoring semantics; report only supported comparisons |
| [KAIS](https://link.springer.com/journal/10115/aims-and-scope) | Next: knowledge discovery over evolving interaction data and reproducible evaluation | Refocus motivation and related work; resolve comparator and robustness gaps; finalize the author list before submission |
| [IJMLC](https://link.springer.com/journal/13042/aims-and-scope) | Following KAIS: learning objectives, representations and stateful intelligent systems | Emphasize the precise learning intervention and its limits; adapt references to author-year style |

## Verified submission differences

JIIS requires LaTeX, a compiled PDF and the complete editable source package;
its page cap includes references, tables and figures. Upload sources without
subdirectories. The guideline page both recommends the Springer Nature template
and names the older macro package's `smallcondensed` option. Resolve that
template ambiguity before freezing pagination.
[JIIS instructions](https://link.springer.com/journal/10844/submission-guidelines).

KAIS recommends LaTeX and also accepts Word. Citations use numeric brackets;
the journal states that authorship changes are not allowed after submission.
[KAIS instructions](https://link.springer.com/journal/10115/submission-guidelines).

IJMLC accepts Word and allows LaTeX for mathematical content. Its references use
author-year citations, so switching requires a bibliography adaptation rather
than replacing the journal name alone. This register identifies Springer
Nature's journal, avoiding similarly named publications elsewhere.
[IJMLC instructions](https://link.springer.com/journal/13042/submission-guidelines).

## Submission controls

Follow the active journal's official submission link when ready. The author
must confirm the author list, affiliations, corresponding author, contributions,
funding and competing interests. Prepare a data-availability statement that
matches the fetch-only dataset policy, and disclose substantive generative
assistance as required by the venue. Do not invent declarations or copy generic
negative declarations without author review.

The earlier [DYU record](DYU-Journal.md) reports author confirmation that the
conference manuscript was not submitted or published. Preserve that record;
reconfirm its continuing accuracy at submission and disclose any later change.
The prior draft is not automatically a published conference predecessor.

Publisher instructions prohibit simultaneous consideration. Fallback activation
follows the decision or confirmed withdrawal recorded in the wiki. The sequence
does not waive source attribution, evidence admission or the
[paper export gate](Paper-Export-Contract.md).

## Current readiness

Venue selection is implemented. JIIS manuscript conversion, scientific-gap
review, author declarations, template verification and immutable snapshot
admission remain open in [JIIS Journal Development](JIIS-Journal.md). Journal
requirements and repository publication checks serve different purposes;
passing either does not automatically satisfy the other.
