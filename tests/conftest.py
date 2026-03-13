"""
Test configuration and fixtures for SigmaHQ RAG application.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import asyncio

# Test data paths
TEST_DATA_DIR = Path(__file__).parent / "files"
TEST_CONFIG_DIR = TEST_DATA_DIR / "config"

# Mock configurations
MOCK_CONFIG = {
    "server": {
        "base_url": "http://localhost:1234",
        "port": 8000,
        "host": "0.0.0.0"
    },
    "rag": {
        "enabled": True,
        "n_results": 3,
        "min_score": 0.1,
        "history_limit": 10,
        "chunk_size": 1000,
        "chunk_overlap": 200
    },
    "logging": {
        "level": "INFO",
        "file": "logs/test.log"
    }
}

MOCK_GITHUB_CONFIG = {
    "repositories": [
        {
            "url": "https://github.com/test/repo.git",
            "branch": "main",
            "file_extensions": [".py", ".js", ".md"],
            "local_path": "data/github/test-repo"
        }
    ]
}


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def test_config_dir():
    """Provide test configuration directory."""
    return TEST_CONFIG_DIR


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    mock_service = Mock()
    mock_service.generate_completion = AsyncMock(return_value="Test response")
    mock_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
    mock_service.is_available = AsyncMock(return_value=True)
    return mock_service


@pytest.fixture
def mock_rag_service():
    """Create a mock RAG service."""
    mock_service = Mock()
    mock_service.query = AsyncMock(return_value=[
        {"text": "Test document", "score": 0.9, "metadata": {}}
    ])
    mock_service.add_documents = AsyncMock(return_value=True)
    mock_service.is_initialized = True
    return mock_service


@pytest.fixture
def mock_chat_service(mock_llm_service, mock_rag_service):
    """Create a mock chat service."""
    mock_service = Mock()
    mock_service.chat = AsyncMock(return_value="Test chat response")
    mock_service.stream_chat = AsyncMock()
    mock_service.add_message = Mock()
    mock_service.get_history = Mock(return_value=[])
    mock_service.clear_history = Mock()
    mock_service.llm_service = mock_llm_service
    mock_service.rag_service = mock_rag_service
    return mock_service


@pytest.fixture
def mock_data_service():
    """Create a mock data service."""
    mock_service = Mock()
    mock_service.process_document = AsyncMock(return_value={"status": "success"})
    mock_service.get_documents = Mock(return_value=[])
    mock_service.delete_document = Mock(return_value=True)
    return mock_service


@pytest.fixture
def mock_config_service():
    """Create a mock config service."""
    mock_service = Mock()
    mock_service.get_config = Mock(return_value=MOCK_CONFIG)
    mock_service.get_config_with_defaults = Mock(return_value=MOCK_CONFIG)
    mock_service.update_config = Mock(return_value=True)
    mock_service.save_config = Mock(return_value=True)
    return mock_service


@pytest.fixture
def mock_logging_service():
    """Create a mock logging service."""
    mock_service = Mock()
    mock_service.get_logger = Mock(return_value=Mock())
    mock_service.get_logs = Mock(return_value=[])
    mock_service.clear_logs = Mock()
    return mock_service


@pytest.fixture
async def async_mock():
    """Create an async mock for testing."""
    async def async_func(*args, **kwargs):
        return "mocked_result"
    
    return AsyncMock(wraps=async_func)


@pytest.fixture
def sample_text_file(temp_dir):
    """Create a sample text file for testing."""
    test_file = temp_dir / "sample.txt"
    test_file.write_text("This is a test document for RAG processing.\n" * 10)
    return test_file


@pytest.fixture
def sample_pdf_file(temp_dir):
    """Create a sample PDF file for testing."""
    # Create a simple PDF content
    pdf_content = b"""
    %PDF-1.4
    1 0 obj
    << /Type /Catalog /Pages 2 0 R >>
    endobj
    2 0 obj
    << /Type /Pages /Kids [3 0 R] /Count 1 >>
    endobj
    3 0 obj
    << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>
    endobj
    4 0 obj
    << /Length 44 >>
    stream
    BT
    /F1 12 Tf
    72 720 Td
    (Test PDF document content) Tj
    ET
    endstream
    endobj
    xref
    0 5
    0000000000 65535 f 
    0000000009 00000 n 
    0000000058 00000 n 
    0000000115 00000 n 
    0000000200 00000 n 
    trailer
    << /Size 5 /Root 1 0 R >>
    startxref
    295
    %%EOF
    """
    test_file = temp_dir / "sample.pdf"
    test_file.write_bytes(pdf_content)
    return test_file


@pytest.fixture
def sample_markdown_file(temp_dir):
    """Create a sample markdown file for testing."""
    markdown_content = """
# Test Document

This is a test markdown document for RAG processing.

## Section 1
This section contains some test content.

## Section 2
This section contains more test content.

```python
def test_function():
    return "test"
```
"""
    test_file = temp_dir / "sample.md"
    test_file.write_text(markdown_content)
    return test_file


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    with patch.dict('os.environ', {
        'LM_STUDIO_BASE_URL': 'http://localhost:1234',
        'LM_STUDIO_API_KEY': 'test-key',
        'CHROMADB_PATH': './data/.chromadb',
        'LOG_LEVEL': 'DEBUG'
    }):
        yield


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# Test utilities
def create_mock_response(status_code=200, json_data=None, text_data=None):
    """Create a mock HTTP response."""
    mock_response = Mock()
    mock_response.status_code = status_code
    mock_response.json = Mock(return_value=json_data or {})
    mock_response.text = text_data or ""
    mock_response.raise_for_status = Mock() if status_code < 400 else Mock(side_effect=Exception("HTTP Error"))
    return mock_response


def assert_async_mock_called_with(mock_obj, *args, **kwargs):
    """Assert that an async mock was called with specific arguments."""
    mock_obj.assert_called_once()
    call_args, call_kwargs = mock_obj.call_args
    assert call_args == args
    assert call_kwargs == kwargs