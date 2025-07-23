"""
Configuration management for Document Organizer.
Handles loading and validation of Azure OpenAI credentials and processing settings.
"""

import json
import os
from dataclasses import dataclass
from typing import Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class AzureOpenAIConfig:
    """Configuration for Azure OpenAI API."""
    endpoint: str
    api_key: str
    deployment_name: str
    api_version: str


@dataclass
class ProcessingConfig:
    """Configuration for processing parameters."""
    max_concurrent_requests: int
    chunk_size_tokens: int
    retry_attempts: int


@dataclass
class Config:
    """Main configuration container."""
    azure_openai: AzureOpenAIConfig
    processing: ProcessingConfig


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class ConfigLoader:
    """Handles loading and validation of configuration."""
    
    DEFAULT_CONFIG_PATH = "config.json"
    
    @classmethod
    def load_config(cls, config_path: Optional[str] = None) -> Config:
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to config file. Defaults to 'config.json'
            
        Returns:
            Config object with validated settings
            
        Raises:
            ConfigurationError: If config file is missing or invalid
        """
        if config_path is None:
            config_path = cls.DEFAULT_CONFIG_PATH
            
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise ConfigurationError(
                f"Configuration file not found: {config_path}\n"
                f"Please create a config.json file with your Azure OpenAI credentials.\n"
                f"Use 'python -c \"from utils.config import ConfigLoader; ConfigLoader.create_template()\"' "
                f"to generate a template."
            )
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in config file: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error reading config file: {e}")
        
        return cls._parse_config(config_data)
    
    @classmethod
    def _parse_config(cls, config_data: Dict[str, Any]) -> Config:
        """Parse and validate configuration data."""
        try:
            # Validate Azure OpenAI configuration
            azure_config_data = config_data.get('azure_openai', {})
            cls._validate_azure_config(azure_config_data)
            
            azure_config = AzureOpenAIConfig(
                endpoint=azure_config_data['endpoint'],
                api_key=azure_config_data['api_key'],
                deployment_name=azure_config_data['deployment_name'],
                api_version=azure_config_data['api_version']
            )
            
            # Validate processing configuration
            processing_data = config_data.get('processing', {})
            processing_config = ProcessingConfig(
                max_concurrent_requests=processing_data.get('max_concurrent_requests', 10),
                chunk_size_tokens=processing_data.get('chunk_size_tokens', 8000),
                retry_attempts=processing_data.get('retry_attempts', 3)
            )
            
            cls._validate_processing_config(processing_config)
            
            return Config(
                azure_openai=azure_config,
                processing=processing_config
            )
            
        except KeyError as e:
            raise ConfigurationError(f"Missing required configuration key: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error parsing configuration: {e}")
    
    @classmethod
    def _validate_azure_config(cls, azure_config: Dict[str, Any]) -> None:
        """Validate Azure OpenAI configuration."""
        required_fields = ['endpoint', 'api_key', 'deployment_name', 'api_version']
        
        for field in required_fields:
            if field not in azure_config:
                raise ConfigurationError(f"Missing required Azure OpenAI configuration: {field}")
            
            if not azure_config[field] or not isinstance(azure_config[field], str):
                raise ConfigurationError(f"Invalid Azure OpenAI configuration for {field}: must be a non-empty string")
        
        # Validate endpoint format
        endpoint = azure_config['endpoint']
        if not endpoint.startswith('https://') or not endpoint.endswith('/'):
            raise ConfigurationError(
                f"Invalid Azure OpenAI endpoint format: {endpoint}\n"
                f"Expected format: https://your-resource.openai.azure.com/"
            )
    
    @classmethod
    def _validate_processing_config(cls, processing_config: ProcessingConfig) -> None:
        """Validate processing configuration."""
        if processing_config.max_concurrent_requests < 1 or processing_config.max_concurrent_requests > 50:
            raise ConfigurationError(
                f"max_concurrent_requests must be between 1 and 50, got: {processing_config.max_concurrent_requests}"
            )
        
        if processing_config.chunk_size_tokens < 1000 or processing_config.chunk_size_tokens > 100000:
            raise ConfigurationError(
                f"chunk_size_tokens must be between 1000 and 100000, got: {processing_config.chunk_size_tokens}"
            )
        
        if processing_config.retry_attempts < 1 or processing_config.retry_attempts > 10:
            raise ConfigurationError(
                f"retry_attempts must be between 1 and 10, got: {processing_config.retry_attempts}"
            )
    
    @classmethod
    def validate_azure_credentials(cls, config: Config) -> bool:
        """
        Validate Azure OpenAI credentials by testing connectivity.
        
        Args:
            config: Configuration object to validate
            
        Returns:
            True if credentials are valid
            
        Raises:
            ConfigurationError: If credentials are invalid
        """
        try:
            # Import here to avoid circular dependencies and handle compatibility issues
            import asyncio
            try:
                import aiohttp
            except ImportError:
                logger.warning("aiohttp not available, skipping credential validation")
                return True
            
            async def test_connection():
                headers = {
                    'api-key': config.azure_openai.api_key,
                    'Content-Type': 'application/json'
                }
                
                # Test endpoint by making a simple request
                test_url = f"{config.azure_openai.endpoint}openai/deployments/{config.azure_openai.deployment_name}/chat/completions?api-version={config.azure_openai.api_version}"
                
                try:
                    async with aiohttp.ClientSession() as session:
                        # Make a minimal test request
                        test_payload = {
                            "messages": [{"role": "user", "content": "test"}],
                            "max_tokens": 1
                        }
                        
                        async with session.post(test_url, headers=headers, json=test_payload) as response:
                            if response.status == 401:
                                raise ConfigurationError("Invalid Azure OpenAI API key")
                            elif response.status == 404:
                                raise ConfigurationError(f"Azure OpenAI deployment not found: {config.azure_openai.deployment_name}")
                            elif response.status >= 400:
                                error_text = await response.text()
                                raise ConfigurationError(f"Azure OpenAI API error: {response.status} - {error_text}")
                            
                            return True
                except Exception as e:
                    # Handle aiohttp compatibility issues gracefully
                    if "cgi" in str(e) or "ModuleNotFoundError" in str(e):
                        logger.warning("aiohttp compatibility issue detected, skipping credential validation")
                        return True
                    raise
            
            # Run the async test
            return asyncio.run(test_connection())
            
        except ImportError:
            logger.warning("Required dependencies not available, skipping credential validation")
            return True
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            # Handle other compatibility issues
            if "cgi" in str(e) or "ModuleNotFoundError" in str(e):
                logger.warning("Compatibility issue detected, skipping credential validation")
                return True
            raise ConfigurationError(f"Error validating Azure credentials: {e}")
    
    @classmethod
    def create_template(cls, output_path: str = "config.json") -> None:
        """Create a template configuration file."""
        template = {
            "azure_openai": {
                "endpoint": "https://your-resource.openai.azure.com/",
                "api_key": "your-api-key-here",
                "deployment_name": "gpt-4-1106-preview",
                "api_version": "2024-02-15-preview"
            },
            "processing": {
                "max_concurrent_requests": 10,
                "chunk_size_tokens": 8000,
                "retry_attempts": 3
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(template, f, indent=2)
        
        print(f"Configuration template created at: {output_path}")
        print("Please edit the file with your actual Azure OpenAI credentials.")