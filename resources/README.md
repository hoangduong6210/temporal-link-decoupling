# Corpus contract

`corpora/` contains local, ignored binary copies. Tracked processed identity is
owned by `manifest.toml` and `checksums.sha256`; reviewed upstream acquisition,
raw digests, HTTP metadata, builder parameters, and the no-redistribution policy
are owned by `source_registry.json`. Set `LINK_PREDICTION_DATA_DIR` to another
complete checksum-verified directory when running elsewhere. Missing data never
triggers an implicit build.

From a clean clone, acquire and rebuild explicitly:

```bash
python experiments/dataset_builders/download.py wikipedia mooc \
  --output-dir resources/corpora
python experiments/dataset_builders/build_coedit.py \
  --input-dir resources/corpora --output-dir resources/corpora
python -m pytest -q tests/test_dataset_acquisition.py
```

The downloader accepts bytes only when their SHA-256 matches the reviewed
registry. The builders use stable event ordering and a fixed NPZ container
encoding, then verify the processed SHA-256. Raw and processed dataset bytes are
not redistributed by this source project because no explicit upstream dataset
license grant was identified; acquisition remains fetch-only from the registered
public upstream endpoints.

Wikipedia and MOOC current files use disjoint user/item node namespaces and the
complete checksum-pinned upstream streams. Truncated migration copies and their
pre-ID-fix predecessors are historical only. CoEdit is rebuilt deterministically
from the current Wikipedia identity, so that input identity and builder settings
remain in its provenance closure.
