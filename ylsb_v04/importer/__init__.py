from .core import ImportResult, SubmissionImporter
from .adapters import AdapterDiagnostic, RawReportError, V03UmeReportAdapter


class RawReportImporter:
    """Route a raw report bundle through an explicit report adapter."""

    def __init__(self, destination=None, *, adapter="v03-ume-report"):
        if adapter != V03UmeReportAdapter.name:
            raise ValueError(f"unknown raw adapter: {adapter}")
        self.destination = destination
        self.adapter = V03UmeReportAdapter()

    def inventory(self, source):
        return self.adapter.inventory(source)

    def import_raw(self, source, *, dry_run=False):
        from pathlib import Path
        import json
        import tempfile

        source_path = Path(source).resolve()
        destination = Path(self.destination).resolve() if self.destination else None
        if destination is not None and source_path.is_dir() and (destination == source_path or source_path in destination.parents):
            raise ValueError("raw input and output paths must be separate")
        if dry_run:
            return {"dry_run": True, "inventory": self.adapter.inventory(source_path)}
        records, inventory = self.adapter.extract(source_path)
        with tempfile.TemporaryDirectory(prefix="ylsb-raw-records-") as temporary:
            payload = Path(temporary) / "adapter-records.jsonl"
            payload.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in records), encoding="utf-8")
            result = SubmissionImporter(destination).import_submission(payload)
        result.source = str(source_path)
        return result, inventory

__all__ = ["AdapterDiagnostic", "ImportResult", "RawReportError", "RawReportImporter", "SubmissionImporter", "V03UmeReportAdapter"]
