"""
Comprehensive error handling and logging system for Document Organizer.
Provides categorized error handling, recovery mechanisms, and detailed logging.
"""

import logging
import os
import sys
import traceback
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import json


class ErrorCategory(Enum):
    """Categories of errors for better handling and reporting."""
    CONFIGURATION = "configuration"
    FILE_PROCESSING = "file_processing"
    OCR_PROCESSING = "ocr_processing"
    API_ERROR = "api_error"
    NETWORK_ERROR = "network_error"
    VALIDATION_ERROR = "validation_error"
    SYSTEM_ERROR = "system_error"
    USER_ERROR = "user_error"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"          # Warning, processing can continue
    MEDIUM = "medium"    # Error, but recoverable
    HIGH = "high"        # Critical error, may stop processing
    CRITICAL = "critical"  # Fatal error, must stop


class ProcessingError(Exception):
    """Base exception for processing errors with categorization."""
    
    def __init__(self, message: str, category: ErrorCategory, 
                 severity: ErrorSeverity, recoverable: bool = True,
                 suggestions: List[str] = None, context: Dict[str, Any] = None):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.recoverable = recoverable
        self.suggestions = suggestions or []
        self.context = context or {}
        self.timestamp = datetime.now()


class ErrorHandler:
    """Comprehensive error handling and logging system."""
    
    def __init__(self, log_dir: str = "logs", enable_checkpoints: bool = True):
        """
        Initialize error handler.
        
        Args:
            log_dir: Directory for log files
            enable_checkpoints: Enable checkpoint system for recovery
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        self.enable_checkpoints = enable_checkpoints
        self.checkpoint_file = self.log_dir / "checkpoint.json"
        
        # Error tracking
        self.error_counts = {category: 0 for category in ErrorCategory}
        self.error_history = []
        self.recovery_attempts = {}
        
        # Setup logging
        self.setup_logging()
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Error handler initialized")
    
    def setup_logging(self):
        """Setup comprehensive logging configuration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Main log file
        main_log = self.log_dir / f"organizer_{timestamp}.log"
        
        # Error-specific log file
        error_log = self.log_dir / f"errors_{timestamp}.log"
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Main log handler (INFO and above)
        main_handler = logging.FileHandler(main_log, encoding='utf-8')
        main_handler.setLevel(logging.INFO)
        main_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        main_handler.setFormatter(main_formatter)
        root_logger.addHandler(main_handler)
        
        # Error log handler (ERROR and above)
        error_handler = logging.FileHandler(error_log, encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        error_handler.setFormatter(error_formatter)
        root_logger.addHandler(error_handler)
        
        # Console handler for user feedback
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Reduce noise from external libraries
        logging.getLogger('aiohttp').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('PIL').setLevel(logging.WARNING)
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None,
                    category: ErrorCategory = None, severity: ErrorSeverity = None,
                    recoverable: bool = None) -> bool:
        """
        Handle an error with categorization and recovery attempts.
        
        Args:
            error: The exception that occurred
            context: Additional context information
            category: Error category (auto-detected if None)
            severity: Error severity (auto-detected if None)
            recoverable: Whether error is recoverable (auto-detected if None)
            
        Returns:
            True if error was handled and processing can continue, False otherwise
        """
        # Auto-detect error properties if not provided
        if isinstance(error, ProcessingError):
            category = error.category
            severity = error.severity
            recoverable = error.recoverable
            context = {**(context or {}), **error.context}
        else:
            category = category or self._categorize_error(error)
            severity = severity or self._assess_severity(error, category)
            recoverable = recoverable if recoverable is not None else self._is_recoverable(error, category)
        
        # Create processing error if needed
        if not isinstance(error, ProcessingError):
            processing_error = ProcessingError(
                str(error), category, severity, recoverable, context=context
            )
        else:
            processing_error = error
        
        # Log the error
        self._log_error(processing_error, context)
        
        # Track error statistics
        self.error_counts[category] += 1
        self.error_history.append({
            'timestamp': processing_error.timestamp,
            'category': category.value,
            'severity': severity.value,
            'message': str(error),
            'recoverable': recoverable,
            'context': context or {}
        })
        
        # Attempt recovery if possible
        if recoverable and severity != ErrorSeverity.CRITICAL:
            return self._attempt_recovery(processing_error)
        
        return False
    
    def _categorize_error(self, error: Exception) -> ErrorCategory:
        """Automatically categorize an error based on its type and message."""
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # Configuration errors
        if any(keyword in error_str for keyword in ['config', 'credential', 'api key', 'endpoint']):
            return ErrorCategory.CONFIGURATION
        
        # File processing errors
        if any(keyword in error_str for keyword in ['file', 'directory', 'path', 'permission']):
            return ErrorCategory.FILE_PROCESSING
        
        # OCR errors
        if any(keyword in error_str for keyword in ['ocr', 'tesseract', 'image', 'pdf']):
            return ErrorCategory.OCR_PROCESSING
        
        # API errors
        if any(keyword in error_str for keyword in ['api', 'openai', 'azure', 'token']):
            return ErrorCategory.API_ERROR
        
        # Network errors
        if any(keyword in error_str for keyword in ['network', 'connection', 'timeout', 'http']):
            return ErrorCategory.NETWORK_ERROR
        
        # Validation errors
        if any(keyword in error_str for keyword in ['validation', 'invalid', 'format']):
            return ErrorCategory.VALIDATION_ERROR
        
        # System errors
        if error_type in ['MemoryError', 'OSError', 'SystemError']:
            return ErrorCategory.SYSTEM_ERROR
        
        return ErrorCategory.USER_ERROR
    
    def _assess_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Assess the severity of an error."""
        error_type = type(error).__name__
        error_str = str(error).lower()
        
        # Critical errors that must stop processing
        if error_type in ['MemoryError', 'SystemError'] or 'critical' in error_str:
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if category == ErrorCategory.CONFIGURATION or 'fatal' in error_str:
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        if category in [ErrorCategory.API_ERROR, ErrorCategory.NETWORK_ERROR]:
            return ErrorSeverity.MEDIUM
        
        # Low severity errors (warnings)
        return ErrorSeverity.LOW
    
    def _is_recoverable(self, error: Exception, category: ErrorCategory) -> bool:
        """Determine if an error is recoverable."""
        error_type = type(error).__name__
        
        # Non-recoverable errors
        if error_type in ['MemoryError', 'SystemError', 'KeyboardInterrupt']:
            return False
        
        # Configuration errors are usually not recoverable during processing
        if category == ErrorCategory.CONFIGURATION:
            return False
        
        # Most other errors are recoverable
        return True
    
    def _log_error(self, error: ProcessingError, context: Dict[str, Any] = None):
        """Log an error with full details."""
        logger = logging.getLogger(__name__)
        
        # Create detailed error message
        error_details = {
            'timestamp': error.timestamp.isoformat(),
            'category': error.category.value,
            'severity': error.severity.value,
            'recoverable': error.recoverable,
            'message': str(error),
            'context': context or {},
            'suggestions': error.suggestions,
            'traceback': traceback.format_exc()
        }
        
        # Log based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR [{error.category.value}]: {error}")
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(f"ERROR [{error.category.value}]: {error}")
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"WARNING [{error.category.value}]: {error}")
        else:
            logger.info(f"INFO [{error.category.value}]: {error}")
        
        # Log detailed information at debug level
        logger.debug(f"Error details: {json.dumps(error_details, indent=2)}")
        
        # Save error details to separate file for analysis
        error_file = self.log_dir / f"error_details_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(error_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(error_details) + '\n')
    
    def _attempt_recovery(self, error: ProcessingError) -> bool:
        """Attempt to recover from an error."""
        recovery_key = f"{error.category.value}_{hash(str(error))}"
        
        # Track recovery attempts
        if recovery_key not in self.recovery_attempts:
            self.recovery_attempts[recovery_key] = 0
        
        self.recovery_attempts[recovery_key] += 1
        
        # Limit recovery attempts
        if self.recovery_attempts[recovery_key] > 3:
            self.logger.warning(f"Max recovery attempts reached for {error.category.value}")
            return False
        
        self.logger.info(f"Attempting recovery for {error.category.value} error (attempt {self.recovery_attempts[recovery_key]})")
        
        # Category-specific recovery strategies
        if error.category == ErrorCategory.FILE_PROCESSING:
            return self._recover_file_processing(error)
        elif error.category == ErrorCategory.OCR_PROCESSING:
            return self._recover_ocr_processing(error)
        elif error.category == ErrorCategory.API_ERROR:
            return self._recover_api_error(error)
        elif error.category == ErrorCategory.NETWORK_ERROR:
            return self._recover_network_error(error)
        
        return False
    
    def _recover_file_processing(self, error: ProcessingError) -> bool:
        """Attempt recovery from file processing errors."""
        # Skip problematic file and continue
        self.logger.info("Skipping problematic file and continuing processing")
        return True
    
    def _recover_ocr_processing(self, error: ProcessingError) -> bool:
        """Attempt recovery from OCR processing errors."""
        # Continue without OCR for this file
        self.logger.info("Continuing without OCR for this file")
        return True
    
    def _recover_api_error(self, error: ProcessingError) -> bool:
        """Attempt recovery from API errors."""
        # Implement exponential backoff
        import time
        import random
        
        attempt = self.recovery_attempts.get(f"api_{hash(str(error))}", 1)
        delay = min(60, (2 ** attempt) + random.uniform(0, 1))
        
        self.logger.info(f"API error recovery: waiting {delay:.1f} seconds before retry")
        time.sleep(delay)
        return True
    
    def _recover_network_error(self, error: ProcessingError) -> bool:
        """Attempt recovery from network errors."""
        # Similar to API error recovery
        return self._recover_api_error(error)
    
    def save_checkpoint(self, state: Dict[str, Any]):
        """Save processing checkpoint for recovery."""
        if not self.enable_checkpoints:
            return
        
        checkpoint_data = {
            'timestamp': datetime.now().isoformat(),
            'state': state,
            'error_counts': {k.value: v for k, v in self.error_counts.items()},
            'recovery_attempts': self.recovery_attempts
        }
        
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, indent=2)
            
            self.logger.debug("Checkpoint saved")
        except Exception as e:
            self.logger.warning(f"Failed to save checkpoint: {e}")
    
    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load processing checkpoint for recovery."""
        if not self.enable_checkpoints or not self.checkpoint_file.exists():
            return None
        
        try:
            with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            # Restore error tracking state
            for category_str, count in checkpoint_data.get('error_counts', {}).items():
                category = ErrorCategory(category_str)
                self.error_counts[category] = count
            
            self.recovery_attempts = checkpoint_data.get('recovery_attempts', {})
            
            self.logger.info("Checkpoint loaded for recovery")
            return checkpoint_data.get('state')
            
        except Exception as e:
            self.logger.warning(f"Failed to load checkpoint: {e}")
            return None
    
    def clear_checkpoint(self):
        """Clear saved checkpoint."""
        if self.checkpoint_file.exists():
            try:
                self.checkpoint_file.unlink()
                self.logger.debug("Checkpoint cleared")
            except Exception as e:
                self.logger.warning(f"Failed to clear checkpoint: {e}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of errors encountered."""
        total_errors = sum(self.error_counts.values())
        
        return {
            'total_errors': total_errors,
            'error_counts_by_category': {k.value: v for k, v in self.error_counts.items()},
            'recovery_attempts': len(self.recovery_attempts),
            'error_history': self.error_history[-10:],  # Last 10 errors
            'most_common_category': max(self.error_counts, key=self.error_counts.get).value if total_errors > 0 else None
        }
    
    def generate_error_report(self) -> str:
        """Generate a comprehensive error report."""
        summary = self.get_error_summary()
        
        report = [
            "Error Handling Report",
            "=" * 50,
            f"Total Errors: {summary['total_errors']}",
            f"Recovery Attempts: {summary['recovery_attempts']}",
            ""
        ]
        
        if summary['total_errors'] > 0:
            report.append("Errors by Category:")
            for category, count in summary['error_counts_by_category'].items():
                if count > 0:
                    report.append(f"  {category}: {count}")
            
            report.append("")
            report.append("Most Common Error Category: " + (summary['most_common_category'] or "None"))
            
            if summary['error_history']:
                report.append("")
                report.append("Recent Errors:")
                for error in summary['error_history'][-5:]:
                    report.append(f"  [{error['category']}] {error['message']}")
        
        return "\n".join(report)


# Convenience functions for common error scenarios
def handle_configuration_error(message: str, suggestions: List[str] = None) -> ProcessingError:
    """Create a configuration error with helpful suggestions."""
    default_suggestions = [
        "Check your config.json file",
        "Run 'python organizer.py --create-config' to generate template",
        "Verify Azure OpenAI credentials"
    ]
    
    return ProcessingError(
        message,
        ErrorCategory.CONFIGURATION,
        ErrorSeverity.HIGH,
        recoverable=False,
        suggestions=suggestions or default_suggestions
    )


def handle_file_error(message: str, file_path: str = None) -> ProcessingError:
    """Create a file processing error."""
    context = {'file_path': file_path} if file_path else {}
    suggestions = [
        "Check file permissions",
        "Verify file exists and is readable",
        "Try with a different file"
    ]
    
    return ProcessingError(
        message,
        ErrorCategory.FILE_PROCESSING,
        ErrorSeverity.MEDIUM,
        recoverable=True,
        suggestions=suggestions,
        context=context
    )


def handle_api_error(message: str, status_code: int = None) -> ProcessingError:
    """Create an API error with retry suggestions."""
    context = {'status_code': status_code} if status_code else {}
    suggestions = [
        "Check your internet connection",
        "Verify Azure OpenAI API key and endpoint",
        "Try reducing concurrent requests",
        "Check Azure OpenAI service status"
    ]
    
    return ProcessingError(
        message,
        ErrorCategory.API_ERROR,
        ErrorSeverity.MEDIUM,
        recoverable=True,
        suggestions=suggestions,
        context=context
    )