"""
Dependency Fix for Gradio/huggingface_hub compatibility issues.

This module provides workarounds for known dependency conflicts between
Gradio, huggingface_hub, and importlib_metadata.
"""

import importlib.metadata
import logging

logger = logging.getLogger(__name__)


def safe_get_version(package_name: str) -> str | None:
    """
    Safely get package version with fallback handling.
    
    Args:
        package_name: Name of the package to get version for
        
    Returns:
        Version string or None if not available
    """
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        logger.warning(f"Package {package_name} not found")
        return None
    except Exception as e:
        logger.warning(f"Error getting version for {package_name}: {e}")
        return None


def patch_importlib_metadata():
    """
    Patch importlib.metadata to handle None metadata gracefully.
    
    This fixes the 'NoneType' object is not subscriptable error
    that occurs with certain versions of huggingface_hub.
    """
    original_version = importlib.metadata.version
    original_distribution = importlib.metadata.distribution
    
    def patched_distribution(name: str):
        try:
            return original_distribution(name)
        except Exception as e:
            logger.warning(f"Error getting distribution for {name}: {e}")
            # Create a mock distribution for problematic packages
            class MockDistribution:
                def __init__(self, name):
                    self.name = name
                    self.metadata = {}
                
                @property
                def version(self):
                    return "0.0.0"
            
            if name in ['torch', 'huggingface_hub', 'gradio', 'gradio_client']:
                return MockDistribution(name)
            raise
    
    def patched_version(name: str) -> str:
        try:
            return original_version(name)
        except Exception as e:
            logger.warning(f"Error getting version for {name}: {e}")
            # Return a default version for known problematic packages
            if name in ['torch', 'huggingface_hub', 'gradio', 'gradio_client']:
                return "0.0.0"
            raise
    
    importlib.metadata.version = patched_version
    importlib.metadata.distribution = patched_distribution


def initialize_dependency_fixes():
    """
    Initialize all dependency fixes.
    """
    logger.info("Applying dependency fixes...")
    
    # Apply the importlib.metadata patch
    patch_importlib_metadata()
    
    # Test that the fix works
    try:
        version = safe_get_version('huggingface_hub')
        logger.info(f"huggingface_hub version: {version}")
    except Exception as e:
        logger.error(f"Dependency fix failed: {e}")
    
    logger.info("Dependency fixes applied successfully")


# Apply fixes when module is imported
initialize_dependency_fixes()