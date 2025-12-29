"""Tests for JSONL storage backend."""

import tempfile
from pathlib import Path

import pytest
from pydantic import BaseModel

from powertools.storage.jsonl import JSONLStore


class SampleModel(BaseModel):
    """Sample model for testing."""

    id: str
    name: str
    value: int = 0


@pytest.fixture
def temp_jsonl_file():
    """Create a temporary JSONL file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test.jsonl"


@pytest.fixture
def store(temp_jsonl_file):
    """Create a JSONLStore with temporary storage."""
    return JSONLStore(temp_jsonl_file, SampleModel)


class TestJSONLStore:
    def test_append_and_list(self, store):
        """Test appending and listing records."""
        record1 = SampleModel(id="1", name="First", value=10)
        record2 = SampleModel(id="2", name="Second", value=20)

        store.append(record1)
        store.append(record2)

        records = store.list_all()
        assert len(records) == 2
        assert records[0].id == "1"
        assert records[1].id == "2"

    def test_get_by_id(self, store):
        """Test retrieving a record by ID."""
        record = SampleModel(id="test-id", name="Test", value=42)
        store.append(record)

        retrieved = store.get_by_id("test-id")
        assert retrieved is not None
        assert retrieved.id == "test-id"
        assert retrieved.name == "Test"
        assert retrieved.value == 42

    def test_get_by_id_not_found(self, store):
        """Test getting a record that doesn't exist."""
        result = store.get_by_id("nonexistent")
        assert result is None

    def test_update(self, store):
        """Test updating a record."""
        record = SampleModel(id="1", name="Original", value=10)
        store.append(record)

        updated = SampleModel(id="1", name="Updated", value=20)
        result = store.update("1", updated)

        assert result is True
        retrieved = store.get_by_id("1")
        assert retrieved.name == "Updated"
        assert retrieved.value == 20

    def test_update_not_found(self, store):
        """Test updating a record that doesn't exist."""
        updated = SampleModel(id="nonexistent", name="Test", value=0)
        result = store.update("nonexistent", updated)
        assert result is False

    def test_delete(self, store):
        """Test deleting a record."""
        record = SampleModel(id="to-delete", name="Delete me", value=0)
        store.append(record)

        result = store.delete("to-delete")
        assert result is True
        assert store.get_by_id("to-delete") is None

    def test_delete_not_found(self, store):
        """Test deleting a record that doesn't exist."""
        result = store.delete("nonexistent")
        assert result is False

    def test_filter(self, store):
        """Test filtering records with a predicate."""
        store.append(SampleModel(id="1", name="Low", value=5))
        store.append(SampleModel(id="2", name="High", value=100))
        store.append(SampleModel(id="3", name="Medium", value=50))

        high_value = store.filter(lambda r: r.value > 40)
        assert len(high_value) == 2
        assert all(r.value > 40 for r in high_value)

    def test_len(self, store):
        """Test getting record count."""
        assert len(store) == 0

        store.append(SampleModel(id="1", name="First", value=0))
        assert len(store) == 1

        store.append(SampleModel(id="2", name="Second", value=0))
        assert len(store) == 2

    def test_iter(self, store):
        """Test iterating over records."""
        store.append(SampleModel(id="1", name="First", value=0))
        store.append(SampleModel(id="2", name="Second", value=0))

        ids = [r.id for r in store]
        assert ids == ["1", "2"]

    def test_creates_parent_directories(self):
        """Test that the store creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "a" / "b" / "c" / "test.jsonl"
            store = JSONLStore(nested_path, SampleModel)

            store.append(SampleModel(id="1", name="Test", value=0))

            assert nested_path.exists()
            assert len(store.list_all()) == 1
