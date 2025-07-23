"""
Unit tests for error handling and logging system.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from utils.error_handler import (
    ErrorHandler, ProcessingError, ErrorCategory, ErrorSeverity,
    handle_configuration_error, handle_file_error, handle_api_error
)


class TestProcessingError(unittest.TestCase):
    """Test cases for ProcessingError class."""
    
    def test_processing_error_creation(self):
        """Test ProcessingError creation with all parameters."""
        suggestions = ["Check config", "Verify credentials"]
        context = {"file": "test.txt", "line": 42}
        
        error = ProcessingError(
            "Test error message",
            ErrorCategory.CONFIGURATION,
            ErrorSeverity.HIGH,
            recoverable=False,
            suggestions=suggestions,
            context=context
        )
        
        self.assertEqual(str(error), "Test error message")
        self.assertEqual(error.category, ErrorCategory.CONFIGURATION)
        self.assertEqual(error.severity, ErrorSeverity.HIGH)
        self.assertFalse(error.recoverable)
        self.assertEqual(error.suggestions, suggestions)
        self.assertEqual(error.context, context)
        self.assertIsNotNone(error.timestamp)
    
    def test_processing_error_defaults(self):
        """Test ProcessingError with default parameters."""
        error = ProcessingError(
            "Simple error",
            ErrorCategory.FILE_PROCESSING,
            ErrorSeverity.MEDIUM
        )
        
        self.assertTrue(error.recoverable)  # Default is True
        self.assertEqual(error.suggestions, [])
        self.assertEqual(error.context, {})


class TestErrorHandler(unittest.TestCase):
    """Test cases for ErrorHandler class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = ErrorHandler(log_dir=self.temp_dir, enable_checkpoints=True)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization."""
        self.assertTrue(Path(self.temp_dir).exists())
        self.assertTrue(self.error_handler.enable_checkpoints)
        self.assertEqual(len(self.error_handler.error_counts), len(ErrorCategory))
        self.assertEqual(self.error_handler.error_history, [])
    
    def test_error_categorization(self):
        """Test automatic error categorization."""
        test_cases = [
            (ValueError("Invalid config file"), ErrorCategory.CONFIGURATION),
            (FileNotFoundError("File not found"), ErrorCategory.FILE_PROCESSING),
            (Exception("OCR processing failed"), ErrorCategory.OCR_PROCESSING),
            (Exception("API key invalid"), ErrorCategory.API_ERROR),
            (Exception("Network timeout"), ErrorCategory.NETWORK_ERROR),
            (ValueError("Invalid format"), ErrorCategory.VALIDATION_ERROR),
            (MemoryError("Out of memory"), ErrorCategory.SYSTEM_ERROR),
            (Exception("Unknown error"), ErrorCategory.USER_ERROR)
        ]
        
        for error, expected_category in test_cases:
            category = self.error_handler._categorize_error(error)
            self.assertEqual(category, expected_category, 
                           f"Error '{error}' should be categorized as {expected_category}")
    
    def test_severity_assessment(self):
        """Test error severity assessment."""
        test_cases = [
            (MemoryError("Out of memory"), ErrorCategory.SYSTEM_ERROR, ErrorSeverity.CRITICAL),
            (ValueError("Config error"), ErrorCategory.CONFIGURATION, ErrorSeverity.HIGH),
            (Exception("API error"), ErrorCategory.API_ERROR, ErrorSeverity.MEDIUM),
            (Exception("File warning"), ErrorCategory.FILE_PROCESSING, ErrorSeverity.LOW)
        ]
        
        for error, category, expected_severity in test_cases:
            severity = self.error_handler._assess_severity(error, category)
            self.assertEqual(severity, expected_severity,
                           f"Error '{error}' should have severity {expected_severity}")
    
    def test_recoverable_assessment(self):
        """Test error recoverability assessment."""
        test_cases = [
            (MemoryError("Out of memory"), ErrorCategory.SYSTEM_ERROR, False),
            (KeyboardInterrupt(), ErrorCategory.USER_ERROR, False),
            (ValueError("Config error"), ErrorCategory.CONFIGURATION, False),
            (FileNotFoundError("File not found"), ErrorCategory.FILE_PROCESSING, True),
            (Exception("API error"), ErrorCategory.API_ERROR, True)
        ]
        
        for error, category, expected_recoverable in test_cases:
            recoverable = self.error_handler._is_recoverable(error, category)
            self.assertEqual(recoverable, expected_recoverable,
                           f"Error '{error}' recoverability should be {expected_recoverable}")
    
    @patch('logging.getLogger')
    def test_error_handling(self, mock_logger):
        """Test complete error handling flow."""
        mock_log = Mock()
        mock_logger.return_value = mock_log
        
        # Test handling a recoverable error
        error = ValueError("Test file error")
        result = self.error_handler.handle_error(
            error,
            context={"file": "test.txt"},
            category=ErrorCategory.FILE_PROCESSING,
            severity=ErrorSeverity.MEDIUM,
            recoverable=True
        )
        
        # Should attempt recovery for recoverable errors
        self.assertTrue(result)
        
        # Check error tracking
        self.assertEqual(self.error_handler.error_counts[ErrorCategory.FILE_PROCESSING], 1)
        self.assertEqual(len(self.error_handler.error_history), 1)
        
        # Test handling a non-recoverable error
        critical_error = MemoryError("Out of memory")
        result = self.error_handler.handle_error(critical_error)
        
        # Should not recover from critical errors
        self.assertFalse(result)
    
    def test_processing_error_handling(self):
        """Test handling of ProcessingError instances."""
        processing_error = ProcessingError(
            "Test processing error",
            ErrorCategory.API_ERROR,
            ErrorSeverity.MEDIUM,
            recoverable=True,
            suggestions=["Check API key"],
            context={"endpoint": "test.com"}
        )
        
        result = self.error_handler.handle_error(processing_error)
        
        # Should use properties from ProcessingError
        self.assertTrue(result)  # Should be recoverable
        self.assertEqual(self.error_handler.error_counts[ErrorCategory.API_ERROR], 1)
    
    def test_recovery_attempts(self):
        """Test recovery attempt limiting."""
        error = ValueError("Persistent error")
        
        # First few attempts should succeed
        for i in range(3):
            result = self.error_handler.handle_error(
                error,
                category=ErrorCategory.FILE_PROCESSING,
                recoverable=True
            )
            self.assertTrue(result, f"Attempt {i+1} should succeed")
        
        # Fourth attempt should fail (max attempts reached)
        result = self.error_handler.handle_error(
            error,
            category=ErrorCategory.FILE_PROCESSING,
            recoverable=True
        )
        self.assertFalse(result, "Should fail after max attempts")
    
    def test_checkpoint_system(self):
        """Test checkpoint save and load functionality."""
        # Test saving checkpoint
        test_state = {
            "processed_files": 10,
            "current_phase": "chunking",
            "chunks_created": 25
        }
        
        self.error_handler.save_checkpoint(test_state)
        
        # Verify checkpoint file was created
        self.assertTrue(self.error_handler.checkpoint_file.exists())
        
        # Test loading checkpoint
        loaded_state = self.error_handler.load_checkpoint()
        self.assertIsNotNone(loaded_state)
        self.assertEqual(loaded_state, test_state)
        
        # Test clearing checkpoint
        self.error_handler.clear_checkpoint()
        self.assertFalse(self.error_handler.checkpoint_file.exists())
    
    def test_checkpoint_disabled(self):
        """Test behavior when checkpoints are disabled."""
        handler = ErrorHandler(log_dir=self.temp_dir, enable_checkpoints=False)
        
        # Should not create checkpoint file
        handler.save_checkpoint({"test": "data"})
        self.assertFalse(handler.checkpoint_file.exists())
        
        # Should return None when loading
        result = handler.load_checkpoint()
        self.assertIsNone(result)
    
    def test_error_summary(self):
        """Test error summary generation."""
        # Generate some errors
        errors = [
            (ValueError("Config error"), ErrorCategory.CONFIGURATION),
            (FileNotFoundError("File error"), ErrorCategory.FILE_PROCESSING),
            (Exception("API error"), ErrorCategory.API_ERROR),
            (ValueError("Another config error"), ErrorCategory.CONFIGURATION)
        ]
        
        for error, category in errors:
            self.error_handler.handle_error(error, category=category)
        
        summary = self.error_handler.get_error_summary()
        
        self.assertEqual(summary['total_errors'], 4)
        self.assertEqual(summary['error_counts_by_category']['configuration'], 2)
        self.assertEqual(summary['error_counts_by_category']['file_processing'], 1)
        self.assertEqual(summary['error_counts_by_category']['api_error'], 1)
        self.assertEqual(summary['most_common_category'], 'configuration')
        self.assertEqual(len(summary['error_history']), 4)
    
    def test_error_report_generation(self):
        """Test error report generation."""
        # Generate some errors
        self.error_handler.handle_error(ValueError("Test error 1"), category=ErrorCategory.CONFIGURATION)
        self.error_handler.handle_error(FileNotFoundError("Test error 2"), category=ErrorCategory.FILE_PROCESSING)
        
        report = self.error_handler.generate_error_report()
        
        self.assertIn("Error Handling Report", report)
        self.assertIn("Total Errors: 2", report)
        self.assertIn("configuration: 1", report)
        self.assertIn("file_processing: 1", report)
        self.assertIn("Recent Errors:", report)
    
    def test_empty_error_report(self):
        """Test error report with no errors."""
        report = self.error_handler.generate_error_report()
        
        self.assertIn("Total Errors: 0", report)
        self.assertNotIn("Recent Errors:", report)


class TestConvenienceFunctions(unittest.TestCase):
    """Test convenience functions for common error scenarios."""
    
    def test_handle_configuration_error(self):
        """Test configuration error helper."""
        error = handle_configuration_error("Invalid API key")
        
        self.assertEqual(error.category, ErrorCategory.CONFIGURATION)
        self.assertEqual(error.severity, ErrorSeverity.HIGH)
        self.assertFalse(error.recoverable)
        self.assertIn("Check your config.json file", error.suggestions)
    
    def test_handle_file_error(self):
        """Test file error helper."""
        error = handle_file_error("File not found", file_path="/path/to/file.txt")
        
        self.assertEqual(error.category, ErrorCategory.FILE_PROCESSING)
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)
        self.assertTrue(error.recoverable)
        self.assertEqual(error.context['file_path'], "/path/to/file.txt")
        self.assertIn("Check file permissions", error.suggestions)
    
    def test_handle_api_error(self):
        """Test API error helper."""
        error = handle_api_error("API request failed", status_code=429)
        
        self.assertEqual(error.category, ErrorCategory.API_ERROR)
        self.assertEqual(error.severity, ErrorSeverity.MEDIUM)
        self.assertTrue(error.recoverable)
        self.assertEqual(error.context['status_code'], 429)
        self.assertIn("Check your internet connection", error.suggestions)


class TestErrorRecovery(unittest.TestCase):
    """Test error recovery mechanisms."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = ErrorHandler(log_dir=self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_file_processing_recovery(self):
        """Test file processing error recovery."""
        error = ProcessingError(
            "File processing failed",
            ErrorCategory.FILE_PROCESSING,
            ErrorSeverity.MEDIUM,
            recoverable=True
        )
        
        result = self.error_handler._recover_file_processing(error)
        self.assertTrue(result)  # Should skip file and continue
    
    def test_ocr_processing_recovery(self):
        """Test OCR processing error recovery."""
        error = ProcessingError(
            "OCR failed",
            ErrorCategory.OCR_PROCESSING,
            ErrorSeverity.MEDIUM,
            recoverable=True
        )
        
        result = self.error_handler._recover_ocr_processing(error)
        self.assertTrue(result)  # Should continue without OCR
    
    @patch('time.sleep')
    def test_api_error_recovery(self, mock_sleep):
        """Test API error recovery with backoff."""
        error = ProcessingError(
            "API rate limited",
            ErrorCategory.API_ERROR,
            ErrorSeverity.MEDIUM,
            recoverable=True
        )
        
        result = self.error_handler._recover_api_error(error)
        self.assertTrue(result)
        mock_sleep.assert_called_once()  # Should implement backoff
    
    @patch('time.sleep')
    def test_network_error_recovery(self, mock_sleep):
        """Test network error recovery."""
        error = ProcessingError(
            "Network timeout",
            ErrorCategory.NETWORK_ERROR,
            ErrorSeverity.MEDIUM,
            recoverable=True
        )
        
        result = self.error_handler._recover_network_error(error)
        self.assertTrue(result)
        mock_sleep.assert_called_once()  # Should implement backoff


if __name__ == '__main__':
    unittest.main()