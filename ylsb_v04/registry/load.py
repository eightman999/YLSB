from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
Adapter = Callable[[str], dict[str, Any] | None]


class Registry:
    """Small exact-alias registry with a future official-source adapter hook.

    Adapters may later import NVIDIA official specifications, Intel ARK, or
    AMD Product Specifications.  They must return a record with provenance;
    this class intentionally performs no fuzzy matching or value inference.
    """

    def __init__(self, kind: str, data: dict[str, Any], adapters: list[Adapter] | None = None):
        self.kind, self.data = kind, data
        self.entries = list(data.get("entries", []))
        self.adapters = list(adapters or [])
        self.by_alias: dict[str, dict[str, Any]] = {}
        for entry in self.entries:
            if not isinstance(entry, dict):
                raise ValueError(f"{kind} registry entries must be objects")
            aliases = [entry.get("canonical_name"), entry.get("reported_name"), *entry.get("aliases", [])]
            for alias in aliases:
                if alias is None:
                    continue
                key = str(alias).strip().casefold()
                if not key:
                    continue
                previous = self.by_alias.get(key)
                if previous is not None and previous.get("canonical_id") != entry.get("canonical_id"):
                    raise ValueError(f"{kind} registry alias collision: {alias}")
                self.by_alias[key] = entry

    def register_adapter(self, adapter: Adapter) -> None:
        self.adapters.append(adapter)

    @staticmethod
    def _entry_provenance(entry: dict[str, Any]) -> dict[str, Any]:
        value = entry.get("provenance")
        if isinstance(value, dict):
            # Preserve field-level provenance verbatim; resolution metadata is
            # stored separately so it cannot overwrite source facts.
            return copy.deepcopy(value)
        source = entry.get("source")
        return {"kind": "registry", "source": source if isinstance(source, str) and source else "registry file"}

    def _field_provenance(self, entry: dict[str, Any]) -> dict[str, Any]:
        existing = entry.get("field_provenance")
        if isinstance(existing, dict):
            return copy.deepcopy(existing)
        source = entry.get("source") if isinstance(entry.get("source"), str) else "registry file"
        fields: dict[str, Any] = {}
        for field, value in entry.items():
            if field in {"provenance", "field_provenance", "aliases", "source"}:
                continue
            if value is None:
                fields[field] = {"kind": "unknown", "reason": "The registry source does not report this field.", "source": source, "source_pointer": f"/{field}"}
            elif self.kind == "models" and field == "bpw":
                fields[field] = {"kind": "inferred", "source": source, "source_pointer": f"/{field}", "reason": "Derived from the quantization label; not a reported source fact."}
            else:
                fields[field] = {"kind": "registry", "source": source, "source_pointer": f"/{field}"}
        return fields

    @staticmethod
    def _require_adapter_provenance(candidate: dict[str, Any]) -> None:
        provenance = candidate.get("provenance")
        if not isinstance(provenance, dict) or provenance.get("kind") not in {"reported", "registry", "derived", "inferred", "unknown"}:
            raise ValueError("registry adapter result must include provenance.kind")
        kind = provenance["kind"]
        if kind == "unknown":
            if not isinstance(provenance.get("reason"), str) or not provenance["reason"].strip():
                raise ValueError("unknown registry adapter values require provenance.reason")
        elif not isinstance(provenance.get("source"), str) or not provenance["source"].strip():
            raise ValueError("registry adapter values require provenance.source")

    def resolve(self, reported_name: str) -> dict[str, Any]:
        key = str(reported_name).strip().casefold()
        entry = self.by_alias.get(key)
        if entry is None:
            for adapter in self.adapters:
                candidate = adapter(str(reported_name))
                if candidate is not None:
                    result = copy.deepcopy(candidate)
                    self._require_adapter_provenance(result)
                    result.setdefault("reported_name", reported_name)
                    result["field_provenance"] = self._field_provenance(result)
                    return result
            return {
                "canonical_id": None,
                "reported_name": reported_name,
                "canonical_name": None,
                "aliases": [],
                "provenance": {"kind": "unknown", "reason": "No exact registry alias; no fuzzy merge or value invention."},
                "resolution": {"match": "unknown"},
            }
        result = copy.deepcopy(entry)
        result["provenance"] = self._entry_provenance(entry)
        result["field_provenance"] = self._field_provenance(entry)
        result["resolution"] = {"match": "exact_alias", "reported_name": reported_name}
        return result


def load_registry(kind: str, path: str | Path | None = None) -> Registry:
    if path is None:
        path = ROOT / "registries" / f"{kind}.json"
    return Registry(kind, json.loads(Path(path).read_text(encoding="utf-8")))


__all__ = ["Registry", "load_registry"]
