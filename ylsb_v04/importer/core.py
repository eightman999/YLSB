from __future__ import annotations

import hashlib
import json
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from ..schema import RECORD_TYPES, migrate_v03_record, validate_normalized_record


def _digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass
class ImportResult:
    fingerprint: str
    duplicate: bool
    records: list[dict[str, Any]]
    source: str
    reason: str | None = None


class SubmissionImporter:
    """Normalize and validate a submission before writing a new corpus file."""

    def __init__(self, destination: str | Path | None = None):
        self.destination = Path(destination) if destination else None

    @staticmethod
    def _safe_extract(source: Path) -> tuple[Path, tempfile.TemporaryDirectory[str] | None]:
        if source.is_dir():
            return source.resolve(), None
        if source.is_file() and source.suffix.lower() in {".json", ".jsonl"}:
            return source.parent.resolve(), None
        if source.suffix.lower() != ".zip":
            raise ValueError(f"submission must be a directory or ZIP: {source}")
        temporary: tempfile.TemporaryDirectory[str] = tempfile.TemporaryDirectory(prefix="ylsb-import-")
        root = Path(temporary.name).resolve()
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                target = (root / member.filename).resolve()
                if target != root and root not in target.parents:
                    temporary.cleanup()
                    raise ValueError(f"ZIP member escapes archive root: {member.filename}")
            archive.extractall(root)
        return root, temporary

    def _protected_destination(self, destination: Path) -> bool:
        parts = destination.resolve().parts
        try:
            index = parts.index("results")
        except ValueError:
            return False
        return len(parts) > index + 2 and parts[index + 1] == "v0.3" and parts[index + 2] in {"frozen", "normalized", "derived"}

    @staticmethod
    def _canonical(value: Any, key: str = "") -> Any:
        """Drop only location metadata so relocation and ZIP prefixes hash alike."""
        if isinstance(value, dict):
            result = {}
            for name, item in value.items():
                lowered = name.lower()
                if lowered in {"relative_path", "source_path", "archive_path"}:
                    continue
                if lowered in {"source", "path"} and (key == "" or key.endswith("provenance") or key in {"source", "artifact"}):
                    continue
                result[name] = SubmissionImporter._canonical(item, name)
            return result
        if isinstance(value, list):
            return [SubmissionImporter._canonical(item, key) for item in value]
        return value

    @classmethod
    def _fingerprint(cls, records: list[dict[str, Any]]) -> str:
        canonical = sorted((cls._canonical(row) for row in records), key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False))
        return _digest({"records": canonical})

    @staticmethod
    def _entity_key(row: dict[str, Any], kind: str) -> tuple[str, str] | None:
        if kind == "model":
            if row.get("record_type") != "model":
                return None
            identifier = row.get("model_id") or (row.get("model") or {}).get("canonical_id")
            details = {field: row.get(field) for field in ("model_id", "canonical_name", "reported_name", "architecture", "quant", "format", "sha256", "file_size_bytes")}
        else:
            if row.get("record_type") != "hardware":
                return None
            identifier = row.get("hardware_id") or (row.get("hardware") or {}).get("canonical_id")
            details = {field: row.get(field) for field in ("hardware_id", "canonical_name", "reported_name", "vendor", "architecture", "vram_each_gb", "memory_type", "memory_bandwidth_gbps", "pcie", "count")}
        if identifier is None:
            return None
        return str(identifier), json.dumps(SubmissionImporter._canonical(details), sort_keys=True, ensure_ascii=False)

    @classmethod
    def _entity_maps(cls, rows: Iterable[dict[str, Any]]) -> tuple[dict[str, str], dict[str, str]]:
        models: dict[str, str] = {}
        hardware: dict[str, str] = {}
        for row in rows:
            for kind, mapping in (("model", models), ("hardware", hardware)):
                item = cls._entity_key(row, kind)
                if item is not None:
                    identifier, descriptor = item
                    previous = mapping.get(identifier)
                    if previous is not None and previous != descriptor:
                        raise ValueError(f"{kind} ID collision for {identifier}")
                    mapping[identifier] = descriptor
        return models, hardware

    @classmethod
    def _validate_references(cls, rows: Iterable[dict[str, Any]], entity_rows: Iterable[dict[str, Any]]) -> None:
        """Check references after entity definitions; runs never define entities."""
        entities = list(entity_rows)
        model_ids = {str(row["model_id"]) for row in entities if row.get("record_type") == "model" and row.get("model_id") is not None}
        hardware_ids = {str(row["hardware_id"]) for row in entities if row.get("record_type") == "hardware" and row.get("hardware_id") is not None}
        machine_ids = {str(row["machine_id"]) for row in entities if row.get("record_type") == "machine" and row.get("machine_id") is not None}
        runtime_ids = {str(row["runtime_id"]) for row in entities if row.get("record_type") == "runtime" and row.get("runtime_id") is not None}
        submission_ids = {str(row["submission_id"]) for row in entities if row.get("record_type") == "submission" and row.get("submission_id") is not None}
        run_ids = {str(row["run_id"]) for row in rows if row.get("record_type") == "run" and row.get("run_id") is not None}
        for row in rows:
            record_type = row.get("record_type")
            if record_type == "run":
                for field, known in (("model_id", model_ids), ("machine_id", machine_ids), ("runtime_id", runtime_ids), ("submission_id", submission_ids)):
                    value = row.get(field)
                    if value is not None and known and str(value) not in known:
                        raise ValueError(f"run reference {field} does not resolve: {value}")
                for group in row.get("hardware", {}).get("gpu_groups", []) if isinstance(row.get("hardware"), dict) else []:
                    value = group.get("canonical_id") if isinstance(group, dict) else None
                    if value is not None and hardware_ids and str(value) not in hardware_ids:
                        raise ValueError(f"run reference hardware canonical_id does not resolve: {value}")
            elif record_type in {"task_result", "performance"}:
                value = row.get("run_id")
                if value is not None and run_ids and str(value) not in run_ids:
                    raise ValueError(f"{record_type} reference run_id does not resolve: {value}")

    @staticmethod
    def _read_records(path: Path) -> list[dict[str, Any]]:
        if path.suffix.lower() == ".jsonl":
            values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            value = json.loads(path.read_text(encoding="utf-8"))
            values = value if isinstance(value, list) else [value]
        if not all(isinstance(value, dict) for value in values):
            raise ValueError(f"JSON records must be objects: {path.name}")
        return values

    @staticmethod
    def _normalize_record(value: Any, relative_path: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("JSON record must be an object")
        record = dict(value)
        record_type = record.get("record_type")
        if record_type is None:
            if "task_id" in record:
                record_type = "task_result"
            elif "measurement_id" in record:
                record_type = "performance"
            elif "run_id" in record:
                record_type = "run"
            else:
                raise ValueError(f"cannot infer record_type for {relative_path}")
        if record_type not in RECORD_TYPES:
            raise ValueError(f"unknown record_type: {record_type}")
        record["record_type"] = record_type
        if record.get("schema_version") == "normalized-corpus-v0.1":
            record = migrate_v03_record(record, source=relative_path)
        elif record.get("schema_version") not in (None, "normalized-corpus-v0.2"):
            raise ValueError(f"unsupported schema_version: {record.get('schema_version')}")
        # A missing version is accepted only as the importer legacy envelope;
        # it is immediately normalized to the current explicit version.
        record["schema_version"] = "normalized-corpus-v0.2"
        if not isinstance(record.get("provenance"), dict) or not record["provenance"]:
            raise ValueError("each imported record needs a non-empty provenance")
        provenance = record["provenance"]
        provenance_items = [provenance] if "kind" in provenance else [item for item in provenance.values() if isinstance(item, dict)]
        for item in provenance_items:
            if item.get("kind") in {"reported", "registry", "derived", "inferred"}:
                item.setdefault("source", relative_path)
            elif item.get("kind") == "unknown" and (not isinstance(item.get("reason"), str) or not item["reason"].strip()):
                raise ValueError("unknown provenance requires a non-empty reason")
        source = record.get("source") if isinstance(record.get("source"), dict) else {}
        record["source"] = {**source, "relative_path": relative_path}
        if record_type == "run":
            if not record.get("run_id"):
                identity = record.get("model_id") or record.get("hardware_id") or relative_path
                record["run_id"] = f"import-{_digest(str(identity))[:16]}"
            record.setdefault("submission_id", None)
            record.setdefault("machine_id", record.get("hardware_id"))
            record.setdefault("model_id", record.get("model_id"))
            record.setdefault("runtime_id", None)
            record.setdefault("config", {})
            record.setdefault("artifacts", {})
        errors = validate_normalized_record(record)
        if errors:
            raise ValueError("record failed schema validation: " + "; ".join(errors))
        return record

    def _existing(self) -> list[dict[str, Any]]:
        if not self.destination or not self.destination.exists():
            return []
        rows: list[dict[str, Any]] = []
        for path in sorted(self.destination.glob("submission-*.jsonl")):
            rows.extend(self._read_records(path))
        return rows

    def import_submission(self, source: str | Path) -> ImportResult:
        source_path = Path(source).resolve()
        root, temporary = self._safe_extract(source_path)
        destination = self.destination.resolve() if self.destination else None
        try:
            if destination is not None:
                if destination == root or root in destination.parents:
                    raise ValueError("input and output paths must be separate")
                if self._protected_destination(destination):
                    raise ValueError("writing imported records into protected v0.3 tree is forbidden")
            if source_path.suffix.lower() in {".json", ".jsonl"}:
                files = [source_path]
            else:
                files = sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".json", ".jsonl"} and (destination is None or destination != path.parent and destination not in path.parents))
            if not files:
                raise ValueError("submission contains no JSON/JSONL records")
            records: list[dict[str, Any]] = []
            for path in files:
                try:
                    values = self._read_records(path)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid JSON in {path.name}: {exc}") from exc
                relative = path.relative_to(root).as_posix()
                records.extend(self._normalize_record(value, relative) for value in values)
            fingerprint = self._fingerprint(records)
            current_models, current_hardware = self._entity_maps(records)
            self._validate_references(records, records)
            existing = self._existing()
            old_models, old_hardware = self._entity_maps(existing)
            for kind, current, old in (("model", current_models, old_models), ("hardware", current_hardware, old_hardware)):
                for identifier, descriptor in current.items():
                    if identifier in old and old[identifier] != descriptor:
                        raise ValueError(f"{kind} ID collision with destination for {identifier}")
            if self.destination:
                self.destination.mkdir(parents=True, exist_ok=True)
                index = self.destination / "import-index.jsonl"
                entries = [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line.strip()] if index.exists() else []
                duplicate = any(row.get("fingerprint") == fingerprint for row in entries)
                reason = "same canonical submission fingerprint already imported" if duplicate else None
                if not duplicate:
                    out = self.destination / f"submission-{fingerprint[:16]}.jsonl"
                    out.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
                    with index.open("a", encoding="utf-8") as handle:
                        handle.write(json.dumps({"fingerprint": fingerprint, "source": source_path.name, "records": len(records)}, ensure_ascii=False) + "\n")
            else:
                reason = None
            return ImportResult(fingerprint, duplicate, records, str(source_path), reason)
        finally:
            if temporary is not None:
                temporary.cleanup()


__all__ = ["ImportResult", "SubmissionImporter"]
