"""
Tests for GitHub repository grid operations.
"""
import pytest
import sys
sys.path.insert(0, '.')
from unittest.mock import MagicMock
from src.nicegui_app.pages.github_repo_page import (
    fetch_github_repositories,
    is_duplicate,
    add_repository,
    update_repository,
    remove_repository,
    save_edits,
    load_config as original_load_config
)
import json
from pathlib import Path

# Mock grid for testing
grid_mock = MagicMock()
grid_mock.options = {'rowData': []}

def test_fetch_github_repositories_with_empty_grid():
    """Test fetching repositories when grid is empty."""
    global grid_mock
    # Simulate empty grid
    grid_mock.options = {'rowData': []}
    
    result = fetch_github_repositories()
    assert result == []

def test_fetch_github_repositories_with_data():
    """Test fetching repositories when grid has data."""
    global grid_mock
    # Simulate grid with repository data
    grid_mock.options = {
        'rowData': [
            {
                'url': 'https://github.com/test/repo',
                'branch': 'main',
                'enabled': True,
                'file_extensions': ['.py']
            }
        ]
    }
    
    result = fetch_github_repositories()
    assert len(result) == 1
    assert result[0]['url'] == 'https://github.com/test/repo'

def test_is_duplicate_with_empty_grid():
    """Test duplicate checking with empty grid."""
    global grid_mock
    grid_mock.options = {'rowData': []}
    
    result = is_duplicate('https://github.com/test/repo', 'main')
    assert result == False

def test_is_duplicate_with_existing_repository():
    """Test duplicate checking with existing repository."""
    global grid_mock
    grid_mock.options = {
        'rowData': [
            {
                'url': 'https://github.com/test/repo',
                'branch': 'main'
            }
        ]
    }
    
    result = is_duplicate('https://github.com/test/repo', 'main')
    assert result == True

def test_is_duplicate_with_different_branch():
    """Test duplicate checking with different branch."""
    global grid_mock
    grid_mock.options = {
        'rowData': [
            {
                'url': 'https://github.com/test/repo',
                'branch': 'main'
            }
        ]
    }
    
    result = is_duplicate('https://github.com/test/repo', 'dev')
    assert result == False

def test_add_repository_to_grid():
    """Test adding a repository to the grid."""
    global grid_mock
    grid_mock.options = {'rowData': []}
    
    result = add_repository('https://github.com/test/repo', 'main', '.py,.md', True)
    assert result == True
    assert len(grid_mock.options['rowData']) == 1
    assert grid_mock.options['rowData'][0]['url'] == 'https://github.com/test/repo'

def test_add_repository_with_duplicate():
    """Test adding a duplicate repository."""
    global grid_mock
    grid_mock.options = {
        'rowData': [
            {
                'url': 'https://github.com/test/repo',
                'branch': 'main'
            }
        ]
    }
    
    result = add_repository('https://github.com/test/repo', 'main', '.py,.md', True)
    assert result == False

def test_update_repository_in_grid():
    """Test updating a repository in the grid."""
    global grid_mock
    grid_mock.options = {
        'rowData': [
            {
                'id': 0,
                'url': 'https://github.com/test/repo',
                'branch': 'main',
                'extensions': '.py'
            }
        ]
    }
    
    result = update_repository(0, 'https://github.com/test/repo', 'dev', '.py,.md', True)
    assert result == True
    assert grid_mock.options['rowData'][0]['branch'] == 'dev'

def test_remove_repository_from_grid():
    """Test removing a repository from the grid."""
    global grid_mock
    grid_mock.options = {
        'rowData': [
            {'id': 0, 'url': 'https://github.com/test/repo1'},
            {'id': 1, 'url': 'https://github.com/test/repo2'}
        ]
    }
    
    result = remove_repository(0)
    assert result == True
    assert len(grid_mock.options['rowData']) == 1
    assert grid_mock.options['rowData'][0]['id'] == 0

def test_save_edits_with_invalid_enabled_state():
    """Test saving edits with invalid enabled state."""
    global grid_mock
    grid_mock.options = {
        'rowData': [
            {'url': 'https://github.com/test/repo', 'branch': 'main', 'enabled': 'invalid'}
        ]
    }
    
    # This should fail validation
    result = save_edits()
    assert result == None  # Function returns None on error
