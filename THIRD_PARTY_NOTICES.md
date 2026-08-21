# Third-Party Notices

This repository installs Python dependencies declared in `pyproject.toml` and
the scientific lock files. Those packages are not redistributed here and
remain governed by their respective upstream licenses.

Dataset bytes are also not redistributed. The Wikipedia and MOOC sources, and
the CoEdit corpus derived from registered inputs, remain outside the project's
BSD 3-Clause grant. Project-authored downloaders, builders, checksums, and
provenance records do not create or imply rights in the underlying data. The
fetch-only policy and known rights status are recorded in
`resources/source_registry.json`.

The self-contained Overleaf package includes the unmodified `IEEEtran.cls`
conference class, version V1.8b. Its source notice states that it is distributed
under the LaTeX Project Public License, version 1.3. The class is stored at
`paper/vendor/IEEEtran.cls`, retains its upstream notices, and is excluded from
the project's BSD 3-Clause grant.

Any future vendored file must retain its original notice and license, and this
document must be updated before release.

The exact boundary of the project license is defined in `LICENSE-SCOPE.md`.
