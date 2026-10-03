"""Timestamp-group protocol and exact candidate support for prospective pilots.

This module is separate from the frozen A003 evaluator. See the wiki contract.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

import numpy as np


def timestamp_groups(timestamps: np.ndarray) -> Iterator[slice]:
    timestamps = np.asarray(timestamps)
    if timestamps.ndim != 1 or not np.isfinite(timestamps).all():
        raise ValueError("timestamps must be a finite vector")
    if np.any(timestamps[1:] < timestamps[:-1]):
        raise ValueError("timestamps must be chronological")
    boundaries = np.r_[0, np.flatnonzero(timestamps[1:] != timestamps[:-1]) + 1,
                       len(timestamps)]
    for start, end in zip(boundaries[:-1], boundaries[1:]):
        if end > start:
            yield slice(int(start), int(end))


def chronological_splits(timestamps: np.ndarray, train_ratio: float = .7,
                         validation_ratio: float = .15) -> dict[str, slice]:
    if not (0 < train_ratio < 1 and 0 < validation_ratio < 1 - train_ratio):
        raise ValueError("invalid split ratios")
    list(timestamp_groups(timestamps))  # validate before selecting boundaries
    n = len(timestamps)
    if n < 3:
        raise ValueError("insufficient events for chronological splits")
    a = int(np.searchsorted(timestamps, timestamps[int(n * train_ratio)], side="left"))
    b = int(np.searchsorted(timestamps, timestamps[int(n * (train_ratio + validation_ratio))],
                            side="left"))
    if not 0 < a < b < n:
        raise ValueError("timestamp ties leave an empty split")
    return {"train": slice(0, a), "validation": slice(a, b), "test": slice(b, n)}


@dataclass(frozen=True)
class CandidateBatch:
    rows: np.ndarray
    negatives: np.ndarray
    skipped_rows: np.ndarray


class DestinationSampler:
    """Read-only sampling; the caller observes a complete timestamp afterwards.

    Catalogue membership is an explicit external-availability assumption. The
    sampler never conditions support on the current target's seen/unseen class.
    """
    def __init__(self, catalogue, *, training_pairs=(), seed: int = 1):
        values = np.asarray(catalogue)
        if values.ndim != 1 or not np.issubdtype(values.dtype, np.integer):
            raise ValueError("destination catalogue must be an integer vector")
        self.catalogue = np.unique(values.astype(np.int64))
        if not len(self.catalogue) or self.catalogue.min() < 0:
            raise ValueError("destination catalogue is empty or invalid")
        self._catalogue = set(self.catalogue.tolist())
        self.training_partners: dict[int, set[int]] = {}
        for source, destination in training_pairs:
            if int(destination) not in self._catalogue:
                raise ValueError("training destination outside catalogue")
            self.training_partners.setdefault(int(source), set()).add(int(destination))
        self.partners: dict[int, set[int]] = {}
        self.rng = np.random.default_rng(seed)
        self.watermark = -np.inf

    def _validate(self, sources, destinations, timestamp):
        if not np.isfinite(timestamp) or timestamp <= self.watermark:
            raise ValueError("score/observe requires an unobserved later timestamp group")
        for values in [sources, destinations]:
            array = np.asarray(values)
            if array.ndim != 1 or not np.issubdtype(array.dtype, np.integer):
                raise ValueError("endpoints must be integer vectors")
        if len(sources) != len(destinations):
            raise ValueError("endpoint lengths differ")
        if any(int(d) not in self._catalogue for d in destinations):
            raise ValueError("destination outside the registered endpoint role")
        if any(int(s) in self._catalogue or int(s) < 0 for s in sources):
            raise ValueError("pilot requires disjoint bipartite source/destination roles")

    def sample(self, sources, destinations, timestamp: float, regime: str) -> CandidateBatch:
        self._validate(sources, destinations, timestamp)
        if regime not in {"random", "historical", "novel-pair"}:
            raise ValueError(f"unknown negative regime: {regime}")
        positives: dict[int, set[int]] = {}
        for source, destination in zip(sources, destinations):
            positives.setdefault(int(source), set()).add(int(destination))
        supports = {}
        for source, current in positives.items():
            if regime == "historical":
                eligible = self.partners.get(source, set()) - current
            elif regime == "novel-pair":
                eligible = self._catalogue - self.training_partners.get(source, set()) - current
            else:
                eligible = self._catalogue - current
            supports[source] = np.asarray(sorted(eligible), dtype=np.int64)
        rows, negatives, skipped = [], [], []
        for row, source in enumerate(sources):
            support = supports[int(source)]
            if not len(support):
                skipped.append(row)
            else:
                rows.append(row)
                negatives.append(int(self.rng.choice(support)))
        return CandidateBatch(np.asarray(rows, dtype=np.int64),
                              np.asarray(negatives, dtype=np.int64),
                              np.asarray(skipped, dtype=np.int64))

    def observe(self, sources, destinations, timestamp: float) -> None:
        self._validate(sources, destinations, timestamp)
        for source, destination in zip(sources, destinations):
            self.partners.setdefault(int(source), set()).add(int(destination))
        self.watermark = float(timestamp)
