"""
Test configuration and fixtures for SigmaHQ RAG application tests.

This module provides test fixtures and configuration that allow tests to run
without external dependencies like LM Studio or ChromaDB.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    with patch.dict(os.environ, {
        'LM_STUDIO_BASE_URL': 'http://localhost:1234',
        'LM_STUDIO_API_KEY': 'test-key',
        'CHROMADB_PATH': './test_data/chromadb',
    }):
        yield


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service for testing."""
    mock_service = Mock()
    mock_service.generate_completion = AsyncMock(return_value="Test response")
    mock_service.generate_embedding = AsyncMock(return_value=[0.1] * 384)
    mock_service.is_available = AsyncMock(return_value=True)
    mock_service.cleanup = Mock()
    return mock_service


@pytest.fixture
def mock_rag_service():
    """Create a mock RAG service for testing."""
    mock_service = Mock()
    mock_service.is_initialized = True
    mock_service.query = AsyncMock(return_value=[
        {"text": "Relevant document content", "score": 0.9, "metadata": {}}
    ])
    mock_service.add_documents = AsyncMock(return_value=True)
    mock_service.cleanup = Mock()
    return mock_service


@pytest.fixture
def sample_text_file():
    """Create a temporary text file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write("This is a test document.\nIt contains multiple lines.\nAnd some content for testing.")
        temp_path = f.name
    
    yield Path(temp_path)
    
    # Cleanup
    if Path(temp_path).exists():
        Path(temp_path).unlink()


@pytest.fixture
def sample_pdf_file():
    """Create a mock PDF file for testing."""
    # Create a minimal PDF file content
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Hello World) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000074 00000 n 
0000000173 00000 n 
0000000301 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
398
%%EOF"""
    
    with tempfile.NamedTemporaryFile(mode='wb', suffix='.pdf', delete=False) as f:
        f.write(pdf_content)
        temp_path = f.name
    
    yield Path(temp_path)
    
    # Cleanup
    if Path(temp_path).exists():
        Path(temp_path).unlink()


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_chromadb():
    """Mock ChromaDB for testing."""
    with patch('chromadb.Client') as mock_chroma:
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.add = Mock()
        mock_collection.query = Mock(return_value={
            'documents': [['Test document content']],
            'distances': [[0.1]],
            'metadatas': [[{'source': 'test.txt'}]]
        })
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chroma.return_value = mock_client
        yield mock_chroma


@pytest.fixture
def mock_aiohttp():
    """Mock aiohttp for testing."""
    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = Mock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "Test response"}}]
        })
        mock_response.raise_for_status = Mock()
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_response)
        mock_session.return_value.__aexit__ = AsyncMock(return_value=None)
        yield mock_session


@pytest.fixture
def test_config():
    """Test configuration that doesn't require external services."""
    return {
        'llm': {
            'model': 'test-model',
            'base_url': 'http://test:1234',
            'api_key': 'test-key',
            'timeout': 10,
            'max_retries': 2,
        },
        'rag': {
            'model': 'test-embedding-model',
            'base_url': 'http://test:1234',
            'api_key': 'test-key',
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'collection_name': 'test_collection',
        },
        'database': {
            'path': './test_data/app.db',
            'max_connections': 5,
            'timeout': 30,
        },
        'file_processor': {
            'allowed_extensions': ['.txt', '.md', '.pdf'],
            'max_file_size_mb': 10,
            'temp_dir': './test_temp',
            'chunk_size': 1000,
            'chunk_overlap': 200,
        },
        'file_storage': {
            'upload_dir': './test_uploads',
            'allowed_extensions': ['.txt', '.md', '.pdf'],
            'max_file_size_mb': 10,
            'max_storage_size_gb': 1,
        },
        'github_client': {
            'api_base_url': 'https://api.github.com',
            'token': 'test-token',
            'rate_limit_delay': 1.0,
        },
        'lm_studio_client': {
            'base_url': 'http://test:1234',
            'timeout': 10,
            'max_retries': 2,
        },
    }


# Test markers for different test categories
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.slow = pytest.mark.slow


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers and skip slow tests by default."""
    if not config.getoption("--run-slow"):
        skip_slow = pytest.mark.skip(reason="need --run-slow option to run")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-slow", action="store_true", default=False,
        help="run slow tests"
    )