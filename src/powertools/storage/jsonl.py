"""JSONL storage backend for tasks and memories."""

from collections.abc import Callable, Iterator
from pathlib import Path

import orjson as json  # noqa: N813 - imported as json for easy reversion
from pydantic import BaseModel


class JSONLStore[T: BaseModel]:
    """Generic JSONL file storage for Pydantic models."""

    def __init__(self, path: Path, model_class: type[T]) -> None:
        self.path = path
        self.model_class = model_class
        self._ensure_file()

    def _ensure_file(self) -> None:
        """Ensure the JSONL file and parent directories exist."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.touch()

    def _read_all(self) -> list[T]:
        """Read all records from the file."""
        records: list[T] = []
        if not self.path.exists():
            return records

        with open(self.path, "rb") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    records.append(self.model_class.model_validate(data))
        return records

    def _write_all(self, records: list[T]) -> None:
        """Write all records to the file (atomic overwrite)."""
        temp_path = self.path.with_suffix(".tmp")
        with open(temp_path, "wb") as f:
            for record in records:
                f.write(json.dumps(record.model_dump()) + b"\n")
        temp_path.replace(self.path)

    def append(self, record: T) -> None:
        """Append a single record to the file."""
        with open(self.path, "ab") as f:
            f.write(json.dumps(record.model_dump()) + b"\n")

    def get_by_id(self, record_id: str, id_field: str = "id") -> T | None:
        """Get a record by its ID field."""
        for record in self._read_all():
            if getattr(record, id_field) == record_id:
                return record
        return None

    def update(self, record_id: str, updated: T, id_field: str = "id") -> bool:
        """Update a record by ID. Returns True if found and updated."""
        records = self._read_all()
        for i, record in enumerate(records):
            if getattr(record, id_field) == record_id:
                records[i] = updated
                self._write_all(records)
                return True
        return False

    def delete(self, record_id: str, id_field: str = "id") -> bool:
        """Delete a record by ID. Returns True if found and deleted."""
        records = self._read_all()
        original_len = len(records)
        records = [r for r in records if getattr(r, id_field) != record_id]
        if len(records) < original_len:
            self._write_all(records)
            return True
        return False

    def list_all(self) -> list[T]:
        """List all records."""
        return self._read_all()

    def filter(self, predicate: Callable[[T], bool]) -> list[T]:
        """Filter records by a predicate function."""
        return [r for r in self._read_all() if predicate(r)]

    def __iter__(self) -> Iterator[T]:
        """Iterate over all records."""
        return iter(self._read_all())

    def __len__(self) -> int:
        """Return count of records."""
        return len(self._read_all())
