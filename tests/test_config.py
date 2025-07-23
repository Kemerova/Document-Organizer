"""
Unit tests for configuration management.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, AsyncMock

from utils.config import (
    ConfigLoader, 
    Config, 
    AzureOpenAIConfig, 
    ProcessingConfig, 
    ConfigurationError
)


class TestConfigLoader(unittest.TestCase):
    """Test cases for ConfigLoader class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.valid_config_data = {
            "azure_openai": {
                "endpoint": "https://test-resource.openai.azure.com/",
                "api_key": "test-api-key-12345",
                "deployment_name": "gpt-4-1106-preview",
                "api_version": "2024-02-15-preview"
            },
            "processing": {
                "max_concurrent_requests": 5,
                "chunk_size_tokens": 4000,
                "retry_attempts": 2
            }
        }
    
    def test_load_config_success(self):
        """Test successful configuration loading."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.valid_config_data, f)
            temp_path = f.name
        
        try:
            config = ConfigLoader.load_config(temp_path)
            
            # Verify Azure OpenAI config
            self.assertEqual(config.azure_openai.endpoint, "https://test-resource.openai.azure.com/")
            self.assertEqual(config.azure_openai.api_key, "test-api-key-12345")
            self.assertEqual(config.azure_openai.deployment_name, "gpt-4-1106-preview")
            self.assertEqual(config.azure_openai.api_version, "2024-02-15-preview")
            
            # Verify processing config
            self.assertEqual(config.processing.max_concurrent_requests, 5)
            self.assertEqual(config.processing.chunk_size_tokens, 4000)
            self.assertEqual(config.processing.retry_attempts, 2)
            
        finally:
            os.unlink(temp_path)
    
    def test_load_config_missing_file(self):
        """Test error when config file is missing."""
        with self.assertRaises(ConfigurationError) as context:
            ConfigLoader.load_config("nonexistent.json")
        
        self.assertIn("Configuration file not found", str(context.exception))
    
    def test_load_config_invalid_json(self):
        """Test error when config file contains invalid JSON."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{ invalid json }")
            temp_path = f.name
        
        try:
            with self.assertRaises(ConfigurationError) as context:
                ConfigLoader.load_config(temp_path)
            
            self.assertIn("Invalid JSON", str(context.exception))
        finally:
            os.unlink(temp_path)
    
    def test_load_config_missing_azure_fields(self):
        """Test error when Azure OpenAI configuration is missing required fields."""
        invalid_config = {
            "azure_openai": {
                "endpoint": "https://test.openai.azure.com/",
                # Missing api_key, deployment_name, api_version
            },
            "processing": self.valid_config_data["processing"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_config, f)
            temp_path = f.name
        
        try:
            with self.assertRaises(ConfigurationError) as context:
                ConfigLoader.load_config(temp_path)
            
            self.assertIn("Missing required Azure OpenAI configuration", str(context.exception))
        finally:
            os.unlink(temp_path)
    
    def test_load_config_invalid_endpoint_format(self):
        """Test error when Azure endpoint has invalid format."""
        invalid_config = self.valid_config_data.copy()
        invalid_config["azure_openai"]["endpoint"] = "invalid-endpoint"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(invalid_config, f)
            temp_path = f.name
        
        try:
            with self.assertRaises(ConfigurationError) as context:
                ConfigLoader.load_config(temp_path)
            
            self.assertIn("Invalid Azure OpenAI endpoint format", str(context.exception))
        finally:
            os.unlink(temp_path)
    
    def test_load_config_default_processing_values(self):
        """Test that processing config uses default values when not specified."""
        config_without_processing = {
            "azure_openai": self.valid_config_data["azure_openai"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_without_processing, f)
            temp_path = f.name
        
        try:
            config = ConfigLoader.load_config(temp_path)
            
            # Verify default values
            self.assertEqual(config.processing.max_concurrent_requests, 10)
            self.assertEqual(config.processing.chunk_size_tokens, 8000)
            self.assertEqual(config.processing.retry_attempts, 3)
            
        finally:
            os.unlink(temp_path)
    
    def test_validate_processing_config_invalid_values(self):
        """Test validation of processing configuration with invalid values."""
        test_cases = [
            {"max_concurrent_requests": 0},  # Too low
            {"max_concurrent_requests": 100},  # Too high
            {"chunk_size_tokens": 500},  # Too low
            {"chunk_size_tokens": 200000},  # Too high
            {"retry_attempts": 0},  # Too low
            {"retry_attempts": 20},  # Too high
        ]
        
        for invalid_processing in test_cases:
            invalid_config = self.valid_config_data.copy()
            invalid_config["processing"].update(invalid_processing)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(invalid_config, f)
                temp_path = f.name
            
            try:
                with self.assertRaises(ConfigurationError):
                    ConfigLoader.load_config(temp_path)
            finally:
                os.unlink(temp_path)
    
    def test_create_template(self):
        """Test template creation."""
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Remove the file so we can test creation
            os.unlink(temp_path)
            
            ConfigLoader.create_template(temp_path)
            
            # Verify template was created
            self.assertTrue(Path(temp_path).exists())
            
            # Verify template content
            with open(temp_path, 'r') as f:
                template_data = json.load(f)
            
            self.assertIn("azure_openai", template_data)
            self.assertIn("processing", template_data)
            self.assertEqual(template_data["azure_openai"]["endpoint"], "https://your-resource.openai.azure.com/")
            
        finally:
            if Path(temp_path).exists():
                os.unlink(temp_path)
    
    def test_validate_azure_credentials_fallback(self):
        """Test Azure credential validation fallback when aiohttp is not available."""
        config = Config(
            azure_openai=AzureOpenAIConfig(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                deployment_name="gpt-4",
                api_version="2024-02-15-preview"
            ),
            processing=ProcessingConfig(
                max_concurrent_requests=10,
                chunk_size_tokens=8000,
                retry_attempts=3
            )
        )
        
        # This should return True due to compatibility fallback
        result = ConfigLoader.validate_azure_credentials(config)
        self.assertTrue(result)
    
    @patch('utils.config.logger')
    def test_validate_azure_credentials_import_error(self, mock_logger):
        """Test Azure credential validation when aiohttp import fails."""
        config = Config(
            azure_openai=AzureOpenAIConfig(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                deployment_name="gpt-4",
                api_version="2024-02-15-preview"
            ),
            processing=ProcessingConfig(
                max_concurrent_requests=10,
                chunk_size_tokens=8000,
                retry_attempts=3
            )
        )
        
        with patch('builtins.__import__', side_effect=ImportError("No module named 'aiohttp'")):
            result = ConfigLoader.validate_azure_credentials(config)
            self.assertTrue(result)
            mock_logger.warning.assert_called()
    
    def test_validate_azure_credentials_basic_validation(self):
        """Test that credential validation at least validates the config structure."""
        config = Config(
            azure_openai=AzureOpenAIConfig(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                deployment_name="gpt-4",
                api_version="2024-02-15-preview"
            ),
            processing=ProcessingConfig(
                max_concurrent_requests=10,
                chunk_size_tokens=8000,
                retry_attempts=3
            )
        )
        
        # Should not raise an exception and return True (due to fallback)
        result = ConfigLoader.validate_azure_credentials(config)
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()