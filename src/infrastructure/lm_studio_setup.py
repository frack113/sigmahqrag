"""
LM Studio Server Setup and Configuration

This module provides utilities for setting up and configuring LM Studio server
for local LLM inference in the SigmaHQ RAG application.
"""

import logging
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)


class LMStudioSetup:
    """LM Studio server setup and configuration utilities."""
    
    def __init__(self, base_url: str = "http://localhost:1234"):
        """
        Initialize LM Studio setup.
        
        Args:
            base_url: Base URL for LM Studio server
        """
        self.base_url = base_url
        self.logger = logging.getLogger(__name__)
    
    def check_server_status(self) -> bool:
        """
        Check if LM Studio server is running.
        
        Returns:
            True if server is running, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=5)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def get_available_models(self) -> list[dict[str, Any]]:
        """
        Get list of available models in LM Studio.
        
        Returns:
            List of available models
        """
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=10)
            if response.status_code == 200:
                return response.json().get("data", [])
            return []
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error getting models: {e}")
            return []
    
    def get_current_model(self) -> str | None:
        """
        Get the currently loaded model.
        
        Returns:
            Name of current model or None
        """
        try:
            response = requests.get(f"{self.base_url}/v1/models", timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get("data", [{}])[0].get("id") if data.get("data") else None
            return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error getting current model: {e}")
            return None
    
    def load_model(self, model_name: str) -> bool:
        """
        Load a model in LM Studio.
        
        Args:
            model_name: Name of the model to load
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        try:
            payload = {"model": model_name}
            response = requests.post(
                f"{self.base_url}/v1/models/load",
                json=payload,
                timeout=60  # Allow time for model loading
            )
            success = response.status_code == 200
            if success:
                self.logger.info(f"Successfully loaded model: {model_name}")
            else:
                self.logger.error(f"Failed to load model {model_name}: {response.text}")
            return success
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error loading model {model_name}: {e}")
            return False
    
    def unload_model(self) -> bool:
        """
        Unload the current model.
        
        Returns:
            True if model unloaded successfully, False otherwise
        """
        try:
            response = requests.post(
                f"{self.base_url}/v1/models/unload",
                timeout=10
            )
            success = response.status_code == 200
            if success:
                self.logger.info("Successfully unloaded model")
            else:
                self.logger.error(f"Failed to unload model: {response.text}")
            return success
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error unloading model: {e}")
            return False
    
    def test_completion(self, prompt: str = "Hello, world!") -> str | None:
        """
        Test completion with current model.
        
        Args:
            prompt: Test prompt
            
        Returns:
            Generated text or None if failed
        """
        try:
            payload = {
                "model": "current",  # Use current model
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 50,
                "temperature": 0.7
            }
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("choices", [{}])[0].get("message", {}).get("content")
            else:
                self.logger.error(f"Completion test failed: {response.text}")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error testing completion: {e}")
            return None
    
    def get_server_info(self) -> dict[str, Any]:
        """
        Get server information.
        
        Returns:
            Dictionary with server information
        """
        info = {
            "server_url": self.base_url,
            "server_running": self.check_server_status(),
            "current_model": None,
            "available_models": [],
            "test_completion": None
        }
        
        if info["server_running"]:
            info["current_model"] = self.get_current_model()
            info["available_models"] = self.get_available_models()
            info["test_completion"] = self.test_completion()
        
        return info
    
    def create_lm_studio_config(self, config_path: str = "data/config/lm_studio.json") -> bool:
        """
        Create LM Studio configuration file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            True if config created successfully, False otherwise
        """
        config_dir = Path(config_path).parent
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config = {
            "server_url": self.base_url,
            "default_model": "mistralai/ministral-3-14b-reasoning",
            "embedding_model": "text-embedding-all-minilm-l6-v2-embedding",
            "timeout": 30,
            "max_tokens": 1000,
            "temperature": 0.7,
            "auto_start": True
        }
        
        try:
            with open(config_path, 'w') as f:
                import json
                json.dump(config, f, indent=2)
            self.logger.info(f"LM Studio config created at: {config_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating LM Studio config: {e}")
            return False
    
    def setup_lm_studio(self) -> dict[str, Any]:
        """
        Complete LM Studio setup process.
        
        Returns:
            Dictionary with setup results
        """
        results = {
            "server_status": False,
            "models_available": False,
            "test_completion": False,
            "config_created": False
        }
        
        self.logger.info("Starting LM Studio setup...")
        
        # Check server status
        results["server_status"] = self.check_server_status()
        if not results["server_status"]:
            self.logger.warning("LM Studio server is not running. Please start LM Studio manually.")
            self.logger.info("1. Download LM Studio from https://lmstudio.ai/")
            self.logger.info("2. Install and start LM Studio")
            self.logger.info("3. Load a model (e.g., mistralai/ministral-3-14b-reasoning)")
            self.logger.info("4. Ensure the server is running on http://localhost:1234")
        
        # Check models
        if results["server_status"]:
            models = self.get_available_models()
            results["models_available"] = len(models) > 0
            if results["models_available"]:
                self.logger.info(f"Found {len(models)} available models")
                for model in models:
                    self.logger.info(f"  - {model.get('id', 'Unknown')}")
            else:
                self.logger.warning("No models available. Please load a model in LM Studio.")
        
        # Test completion
        if results["server_status"] and results["models_available"]:
            test_result = self.test_completion()
            results["test_completion"] = test_result is not None
            if results["test_completion"]:
                self.logger.info("LM Studio completion test successful")
            else:
                self.logger.warning("LM Studio completion test failed")
        
        # Create config
        results["config_created"] = self.create_lm_studio_config()
        
        self.logger.info("LM Studio setup completed")
        return results


def setup_lm_studio_server() -> dict[str, Any]:
    """
    Convenience function to set up LM Studio server.
    
    Returns:
        Dictionary with setup results
    """
    setup = LMStudioSetup()
    return setup.setup_lm_studio()


if __name__ == "__main__":
    # Test LM Studio setup
    results = setup_lm_studio_server()
    print("LM Studio Setup Results:")
    for key, value in results.items():
        print(f"  {key}: {value}")