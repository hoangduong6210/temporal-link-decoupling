---
title: License and Assets
status: canonical public licensing policy
last_updated: 2026-08-21
paper_source: false
---

# License and Assets

Project-authored software and supporting material are released under the
[BSD 3-Clause License](../../LICENSE). The exact path-level boundary is defined
in [`LICENSE-SCOPE.md`](../../LICENSE-SCOPE.md). In particular, the grant covers
the implementation, runners, tests, project configuration and protocols,
documentation, dataset builders, checksums, registries, and provenance metadata
written for this project.

Frozen evidence, execution evidence, and conference artifacts are excluded
from the software grant. Their inclusion supports inspection and scientific
reproducibility; it does not by itself grant reuse or redistribution rights.

Dataset acquisition is closed under a conservative fetch-only policy recorded
in [`resources/source_registry.json`](../../resources/source_registry.json).
The registry pins the public upstream page, exact raw URLs and digests,
retrieval metadata, citation notice, builders, and processed identities. No
explicit upstream dataset license grant was identified, so raw or processed
dataset bytes must not be redistributed by this project. A future
redistribution decision requires a reviewed rights record and a new registry
identity.

Third-party dependencies are installed separately and retain their upstream
licenses. The unmodified IEEE conference class bundled for Overleaf retains its
LaTeX Project Public License notice and is outside the BSD grant. A future
vendored asset must retain its original notice and be registered in
[`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md). Nothing in the project
license relicenses a dataset, dependency, external asset, or excluded artifact.
