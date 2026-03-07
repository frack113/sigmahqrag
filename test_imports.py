#!/usr/bin/env python
"""Test script to verify all imports work correctly."""
import sys
sys.path.insert(0, 'src')

print("Testing imports...")

try:
    from nicegui_app.models import chat_service, data_service, rag_service, file_processor, llm_service
    print("✓ All model imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

try:
    from nicegui_app.components import card, chat_message, file_upload, notification
    print("✓ All component imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

try:
    from nicegui_app.pages import chat_page, github_repo_page
    print("✓ All page imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

try:
    from nicegui_app import app
    print("✓ Main app imports successful")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

print("\n✓✓✓ All imports successful! ✓✓✓")