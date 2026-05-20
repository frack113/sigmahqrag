import pytest
from pathlib import Path
from src.back.database.service import DatabaseService
from src.back.database.buffered_service import BufferedDatabaseService

@pytest.fixture
def temp_db(tmp_path):
    """Fixture to provide a clean, temporary DatabaseService."""
    db_file = tmp_path / "test_sigma.duckdb"
    # Since DatabaseService is a highly coupled singleton, we must be very careful.
    service = DatabaseService(str(db_file))
    service._writer_conn.execute(open("src/back/database/initdb.sql").read())
    service._writer_conn.commit()
    yield service
    # Cleanup singleton instance for next test to avoid pollution
    DatabaseService._instance = None
    service.close()

@pytest.fixture
def buffered_db(temp_db, tmp_path):
    """Fixture to provide a BufferedDatabaseService."""
    journal_path = tmp_path / "test_journal.log"
    return BufferedDatabaseService(temp_db, journal_path)

def test_write_through_mode(buffered_db):
    """Test that write-through mode updates DB immediately."""
    worker_id = "worker_1"
    state = {"status": "running"}
    
    buffered_db.upsert_worker_state(worker_id, state, mode="write-through")
    
    retrieved = buffered_db.db.get_worker_state(worker_id)
    assert retrieved is not None    assert retrieved["status"] == "running"

def test_write_back_mode(buffered_db):
    """Test that write-back mode updates cache but not DB until flush."""
    worker_id = "worker_2"
    state = {"status": "running"}
    
    buffered_db.upsert_worker_state(worker_id, state, mode="write-back")
    
    # Check cache via internal access (for testing)
    assert buffered_db.cache[f"worker_state:{worker_id}"] == state
    
    # Check underlying DB (should NOT be updated yet)
    retrieved = buffered_db.db.get_worker_state(worker_id)
    assert retrieved is None

def test_flush_mode(buffered_db):
    """Test that flush synchronizes cache to DB."""
    worker_id = "worker_3"
    state = {"status": "running"}
    
    buffered_db.upsert_worker_state(worker_id, state, mode="write-back")
    assert len(buffered_db.cache) == 1
    
    buffered_db.flush()
    
    # Check cache is empty
    assert len(buffered_db.cache) == 0
    
    # Check underlying DB is updated
    retrieved = buffered_db.db.get_worker_state(worker_id)
    assert retrieved["status"] == "running"

def test_recovery_mode(temp_db, tmp_path):
    """Test that recovery replays the journal."""
    journal_path = tmp_path / "test_journal.log"
    
    # 1. Simulate a crash by manually writing to the journal
    with open(journal_path, "a", encoding="utf-8") as f:
        f.write("upsert_worker_state|('worker_recovery',)|{'state': {'status': 'recovered'}}\n")
    
    # 2. Initialize BufferedDatabaseService (which triggers _check_recovery)
    buffered_db = BufferedDatabaseService(temp_db, journal_path)
    
    # 3. Check if the state was recovered into DB
    retrieved = temp_db.get_worker_state("worker_recovery")
    assert retrieved is not None
    assert retrieved["status"] == "recovered"
