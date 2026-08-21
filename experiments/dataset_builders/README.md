# Dataset builders

These entry points are the explicit, checksum-locked clean-clone acquisition
path documented in `resources/README.md`. They never run implicitly from the
training loader. `download.py` accepts only raw bytes registered in
`resources/source_registry.json`; both builders verify deterministic processed
artifact identities before returning.

These are migrated provenance utilities, not an implicit runtime path. They stage
outputs under `resources/staging/`; they never overwrite the checksum-pinned corpus.
Promote a staged file only after recording its raw-source digest, license, builder
revision, processed checksum, and dataset-registry review. `apply_idfix.py` reads the
preserved inputs under `resources/corpora/pre_idfix/`.

The upstream raw-file digests are registered in
`resources/source_registry.json`; no upstream redistribution license was
identified. Keep acquisition fetch-only and do not commit raw or derived corpus
bytes. `download.py` rejects any raw CSV that does not match the registered
digest.
