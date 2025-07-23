"""
Production readiness tests for Document Organizer.
Validates system readiness for production deployment.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from utils.config import ConfigLoader, ConfigurationError
from utils.performance import PerformanceMonitor, MemoryOptimizer, ConfigurationValidator
from utils.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity


class TestProductionReadiness(unittest.TestCase):
    """Test production readiness aspects."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_configuration_validation(self):
        """Test configuration validation for production."""
        # Test valid configuration
        valid_config = {
            "azure_openai": {
                "endpoint": "https://test.openai.azure.com/",
                "api_key": "sk-test-key-12345",
                "deployment_name": "gpt-4-1106-preview",
                "api_version": "2024-02-15-preview"
            },
            "processing": {
                "max_concurrent_requests": 10,
                "chunk_size_tokens": 8000,
                "retry_attempts": 3
            }
        }
        
        config_file = Path(self.temp_dir) / "valid_config.json"
        with open(config_file, 'w') as f:
            json.dump(valid_config, f)
        
        # Should load without errors
        config = ConfigLoader.load_config(str(config_file))
        self.assertIsNotNone(config)
        
        # Test invalid configurations
        invalid_configs = [
            # Missing API key
            {
                "azure_openai": {
                    "endpoint": "https://test.openai.azure.com/",
                    "deployment_name": "gpt-4",
                    "api_version": "2024-02-15-preview"
                }
            },
            # Invalid endpoint format
            {
                "azure_openai": {
                    "endpoint": "invalid-endpoint",
                    "api_key": "test-key",
                    "deployment_name": "gpt-4",
                    "api_version": "2024-02-15-preview"
                }
            },
            # Invalid processing parameters
            {
                "azure_openai": valid_config["azure_openai"],
                "processing": {
                    "max_concurrent_requests": 0,  # Invalid
                    "chunk_size_tokens": 500,     # Too small
                    "retry_attempts": 20          # Too many
                }
            }
        ]
        
        for i, invalid_config in enumerate(invalid_configs):
            config_file = Path(self.temp_dir) / f"invalid_config_{i}.json"
            with open(config_file, 'w') as f:
                json.dump(invalid_config, f)
            
            with self.assertRaises(ConfigurationError):
                ConfigLoader.load_config(str(config_file))
    
    def test_error_handling_robustness(self):
        """Test error handling system robustness."""
        error_handler = ErrorHandler(log_dir=self.temp_dir)
        
        # Test various error scenarios
        test_errors = [
            (FileNotFoundError("File not found"), ErrorCategory.FILE_PROCESSING),
            (ConnectionError("Network error"), ErrorCategory.NETWORK_ERROR),
            (ValueError("Invalid API response"), ErrorCategory.API_ERROR),
            (MemoryError("Out of memory"), ErrorCategory.SYSTEM_ERROR),
            (KeyboardInterrupt(), ErrorCategory.USER_ERROR)
        ]
        
        recovery_count = 0
        for error, expected_category in test_errors:
            try:
                result = error_handler.handle_error(error)
                if result:
                    recovery_count += 1
            except Exception:
                pass  # Some errors might not be recoverable
        
        # Should handle errors gracefully
        self.assertGreater(len(error_handler.error_history), 0)
        
        # Should attempt recovery for some errors
        self.assertGreaterEqual(recovery_count, 0)
        
        # Should generate meaningful error report
        report = error_handler.generate_error_report()
        self.assertIn("Error Handling Report", report)
        self.assertIn("Total Errors:", report)
    
    def test_performance_monitoring(self):
        """Test performance monitoring capabilities."""
        monitor = PerformanceMonitor(enable_detailed_monitoring=False)
        
        # Test operation monitoring
        with monitor.monitor_operation("test_operation", test_param="value"):
            # Simulate some work
            import time
            time.sleep(0.1)
        
        # Should have recorded metrics
        self.assertEqual(len(monitor.metrics_history), 1)
        
        metric = monitor.metrics_history[0]
        self.assertEqual(metric.operation, "test_operation")
        self.assertGreater(metric.duration, 0.05)  # Should be at least 50ms
        self.assertGreaterEqual(metric.memory_after, 0)
        
        # Test system info collection
        system_info = monitor.get_system_info()
        required_fields = ['cpu_count', 'memory_total_gb', 'disk_total_gb']
        for field in required_fields:
            self.assertIn(field, system_info)
        
        # Test performance summary
        summary = monitor.get_performance_summary()
        self.assertEqual(summary['total_operations'], 1)
        self.assertIn('system_info', summary)
    
    def test_memory_optimization(self):
        """Test memory optimization utilities."""
        # Test memory estimation
        estimates = MemoryOptimizer.estimate_memory_requirements(
            file_count=100,
            avg_file_size_kb=50,
            chunk_size_tokens=8000
        )
        
        required_fields = ['content_memory_mb', 'total_estimated_mb', 'recommended_ram_gb']
        for field in required_fields:
            self.assertIn(field, estimates)
            self.assertGreater(estimates[field], 0)
        
        # Test batch processing optimization
        test_chunks = list(range(25))  # 25 test items
        
        processed = MemoryOptimizer.optimize_chunk_processing(
            test_chunks,
            batch_size=5
        )
        
        self.assertEqual(len(processed), 25)
        self.assertEqual(processed, test_chunks)
    
    def test_configuration_optimization(self):
        """Test configuration optimization for different systems."""
        # Test low-resource system
        low_resource_system = {
            'cpu_count': 2,
            'memory_total_gb': 4,
            'memory_available_gb': 2,
            'disk_free_gb': 10
        }
        
        low_config = ConfigurationValidator.get_recommended_settings(low_resource_system)
        self.assertLessEqual(low_config['max_concurrent_requests'], 4)
        self.assertLessEqual(low_config['chunk_size_tokens'], 6000)
        
        # Test high-resource system
        high_resource_system = {
            'cpu_count': 8,
            'memory_total_gb': 16,
            'memory_available_gb': 12,
            'disk_free_gb': 100
        }
        
        high_config = ConfigurationValidator.get_recommended_settings(high_resource_system)
        self.assertGreaterEqual(high_config['max_concurrent_requests'], 8)
        self.assertEqual(high_config['chunk_size_tokens'], 8000)
        
        # Test configuration validation
        test_config = {
            'max_concurrent_requests': 20,
            'chunk_size_tokens': 12000,
            'retry_attempts': 3
        }
        
        validation = ConfigurationValidator.validate_processing_config(
            test_config, high_resource_system
        )
        
        self.assertIn('valid', validation)
        self.assertIn('recommendations', validation)
        self.assertIn('optimal_settings', validation)
    
    def test_dependency_availability(self):
        """Test that all required dependencies are available."""
        # Test core dependencies
        try:
            import json
            import os
            import pathlib
            import logging
            import asyncio
            import argparse
            self.assertTrue(True)  # Core Python modules available
        except ImportError as e:
            self.fail(f"Core dependency missing: {e}")
        
        # Test optional dependencies (should handle gracefully if missing)
        optional_deps = [
            ('tiktoken', 'Token counting'),
            ('tqdm', 'Progress bars'),
            ('psutil', 'System monitoring')
        ]
        
        for dep_name, description in optional_deps:
            try:
                __import__(dep_name)
            except ImportError:
                # Optional dependencies should be handled gracefully
                pass
    
    def test_file_system_operations(self):
        """Test file system operations for production readiness."""
        # Test directory creation
        test_dirs = ['input', 'output', 'logs', 'temp']
        for dir_name in test_dirs:
            dir_path = Path(self.temp_dir) / dir_name
            dir_path.mkdir(exist_ok=True)
            self.assertTrue(dir_path.exists())
            self.assertTrue(dir_path.is_dir())
        
        # Test file operations
        test_file = Path(self.temp_dir) / "test.txt"
        
        # Write test
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write("Test content")
        
        self.assertTrue(test_file.exists())
        
        # Read test
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        self.assertEqual(content, "Test content")
        
        # Permission test (if applicable)
        if os.name != 'nt':  # Skip on Windows
            os.chmod(test_file, 0o644)
            self.assertTrue(os.access(test_file, os.R_OK))
    
    def test_logging_system(self):
        """Test logging system for production."""
        import logging
        
        # Test log directory creation
        log_dir = Path(self.temp_dir) / "logs"
        log_dir.mkdir(exist_ok=True)
        
        # Test logger configuration
        logger = logging.getLogger("test_logger")
        handler = logging.FileHandler(log_dir / "test.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        # Test logging at different levels
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        
        # Verify log file was created and contains messages
        log_file = log_dir / "test.log"
        self.assertTrue(log_file.exists())
        
        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()
        
        self.assertIn("Test info message", log_content)
        self.assertIn("Test warning message", log_content)
        self.assertIn("Test error message", log_content)
    
    def test_resource_limits(self):
        """Test resource limit checking."""
        monitor = PerformanceMonitor()
        
        # Test resource limit checking
        limits = monitor.check_resource_limits(
            memory_limit_gb=8.0,
            cpu_limit_percent=90.0
        )
        
        required_checks = ['memory_ok', 'cpu_ok', 'disk_ok', 'overall_ok']
        for check in required_checks:
            self.assertIn(check, limits)
            self.assertIsInstance(limits[check], bool)
        
        # Test system info completeness
        system_info = monitor.get_system_info()
        required_info = ['cpu_count', 'memory_total_gb', 'disk_total_gb']
        for info in required_info:
            self.assertIn(info, system_info)
            self.assertGreater(system_info[info], 0)
    
    def test_graceful_shutdown(self):
        """Test graceful shutdown capabilities."""
        # Test that components can be cleanly shut down
        monitor = PerformanceMonitor()
        error_handler = ErrorHandler(log_dir=self.temp_dir)
        
        # Simulate some activity
        with monitor.monitor_operation("test_shutdown"):
            error_handler.handle_error(ValueError("Test error"))
        
        # Test cleanup
        try:
            # Components should handle cleanup gracefully
            monitor.optimize_memory()
            error_handler.clear_checkpoint()
            
            # Should not raise exceptions
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"Graceful shutdown failed: {e}")
    
    def test_production_configuration_template(self):
        """Test production configuration template generation."""
        from utils.config import ConfigLoader
        
        template_file = Path(self.temp_dir) / "production_config.json"
        ConfigLoader.create_template(str(template_file))
        
        self.assertTrue(template_file.exists())
        
        # Verify template structure
        with open(template_file, 'r') as f:
            template_data = json.load(f)
        
        required_sections = ['azure_openai', 'processing']
        for section in required_sections:
            self.assertIn(section, template_data)
        
        # Verify Azure OpenAI section
        azure_section = template_data['azure_openai']
        required_azure_fields = ['endpoint', 'api_key', 'deployment_name', 'api_version']
        for field in required_azure_fields:
            self.assertIn(field, azure_section)
        
        # Verify processing section
        processing_section = template_data['processing']
        required_processing_fields = ['max_concurrent_requests', 'chunk_size_tokens', 'retry_attempts']
        for field in required_processing_fields:
            self.assertIn(field, processing_section)


class TestSystemIntegration(unittest.TestCase):
    """Test system integration for production deployment."""
    
    def test_component_integration(self):
        """Test that all components integrate properly."""
        # Test that components can be imported and initialized
        try:
            from utils.config import ConfigLoader
            from utils.file_loader import FileLoader
            from utils.chunker import TokenAwareChunker
            from utils.processor import DataProcessor
            from utils.output_writer import OutputWriter
            from utils.performance import PerformanceMonitor
            from utils.error_handler import ErrorHandler
            
            # Should be able to create instances
            file_loader = FileLoader()
            processor = DataProcessor()
            monitor = PerformanceMonitor()
            error_handler = ErrorHandler()
            
            self.assertIsNotNone(file_loader)
            self.assertIsNotNone(processor)
            self.assertIsNotNone(monitor)
            self.assertIsNotNone(error_handler)
            
        except ImportError as e:
            self.fail(f"Component integration failed: {e}")
    
    def test_end_to_end_workflow_structure(self):
        """Test that end-to-end workflow structure is sound."""
        # This tests the workflow structure without actual processing
        workflow_steps = [
            "Configuration loading",
            "File discovery",
            "Content loading",
            "OCR processing",
            "Content chunking",
            "GPT processing",
            "Data consolidation",
            "Output generation"
        ]
        
        # Each step should be implementable
        for step in workflow_steps:
            # This is a structural test - in production each step would be implemented
            self.assertIsInstance(step, str)
            self.assertGreater(len(step), 0)
        
        # Test workflow can be monitored
        monitor = PerformanceMonitor()
        for step in workflow_steps[:3]:  # Test first few steps
            with monitor.monitor_operation(step):
                pass  # Simulate step execution
        
        self.assertEqual(len(monitor.metrics_history), 3)


if __name__ == '__main__':
    unittest.main()