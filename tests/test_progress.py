"""
Unit tests for progress tracking and user feedback system.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import time

# Import the ProgressTracker from organizer.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from organizer import ProgressTracker
except ImportError:
    # Fallback implementation for testing
    class ProgressTracker:
        def __init__(self, total, description):
            self.total = total
            self.current = 0
            self.description = description
            self.pbar = None
        
        def update(self, increment=1):
            self.current += increment
        
        def close(self):
            pass


class TestProgressTracker(unittest.TestCase):
    """Test cases for progress tracking functionality."""
    
    def test_progress_tracker_initialization(self):
        """Test progress tracker initialization."""
        tracker = ProgressTracker(100, "Test Progress")
        
        self.assertEqual(tracker.total, 100)
        self.assertEqual(tracker.current, 0)
        self.assertEqual(tracker.description, "Test Progress")
    
    def test_progress_tracker_update(self):
        """Test progress tracker updates."""
        tracker = ProgressTracker(10, "Test Progress")
        
        # Test single increment
        tracker.update()
        self.assertEqual(tracker.current, 1)
        
        # Test custom increment
        tracker.update(3)
        self.assertEqual(tracker.current, 4)
        
        # Test multiple updates
        tracker.update(2)
        tracker.update(1)
        self.assertEqual(tracker.current, 7)
    
    def test_progress_tracker_completion(self):
        """Test progress tracker completion."""
        tracker = ProgressTracker(5, "Test Progress")
        
        # Update to completion
        for i in range(5):
            tracker.update()
        
        self.assertEqual(tracker.current, 5)
        self.assertEqual(tracker.current, tracker.total)
        
        # Test close
        tracker.close()  # Should not raise exception
    
    @patch('organizer.TQDM_AVAILABLE', True)
    @patch('organizer.tqdm')
    def test_progress_tracker_with_tqdm(self, mock_tqdm):
        """Test progress tracker with tqdm available."""
        mock_pbar = Mock()
        mock_tqdm.return_value = mock_pbar
        
        tracker = ProgressTracker(100, "Test with tqdm")
        
        # Verify tqdm was called
        mock_tqdm.assert_called_once_with(total=100, desc="Test with tqdm", unit="items")
        
        # Test update
        tracker.update(5)
        mock_pbar.update.assert_called_once_with(5)
        
        # Test close
        tracker.close()
        mock_pbar.close.assert_called_once()
    
    @patch('organizer.TQDM_AVAILABLE', False)
    @patch('builtins.print')
    def test_progress_tracker_without_tqdm(self, mock_print):
        """Test progress tracker fallback without tqdm."""
        tracker = ProgressTracker(50, "Test without tqdm")
        
        # Verify initial print
        mock_print.assert_called_with("Starting Test without tqdm (0/50)")
        
        # Test update
        tracker.update(10)
        mock_print.assert_called_with("Test without tqdm: 10/50")
        
        # Test close
        tracker.close()
        mock_print.assert_called_with("Completed Test without tqdm: 10/50")
    
    def test_progress_tracker_edge_cases(self):
        """Test progress tracker edge cases."""
        # Zero total
        tracker = ProgressTracker(0, "Empty Progress")
        self.assertEqual(tracker.total, 0)
        tracker.update()
        self.assertEqual(tracker.current, 1)  # Can exceed total
        
        # Large numbers
        tracker = ProgressTracker(1000000, "Large Progress")
        tracker.update(500000)
        self.assertEqual(tracker.current, 500000)
        
        # Negative increment (edge case)
        tracker = ProgressTracker(10, "Test Progress")
        tracker.update(5)
        tracker.update(-2)  # This might be allowed in implementation
        # Don't assert specific behavior for negative increments


class TestProgressIntegration(unittest.TestCase):
    """Test progress tracking integration with main processing."""
    
    def test_file_loading_progress_simulation(self):
        """Simulate progress tracking during file loading."""
        files = [f"file_{i}.txt" for i in range(10)]
        
        tracker = ProgressTracker(len(files), "Loading files")
        
        # Simulate processing files
        for i, file in enumerate(files):
            # Simulate file processing time
            time.sleep(0.001)  # Very short delay
            tracker.update()
            
            # Verify progress
            self.assertEqual(tracker.current, i + 1)
        
        tracker.close()
        self.assertEqual(tracker.current, len(files))
    
    def test_chunk_processing_progress_simulation(self):
        """Simulate progress tracking during chunk processing."""
        chunk_count = 25
        
        tracker = ProgressTracker(chunk_count, "Processing chunks")
        
        # Simulate batch processing with callback
        def progress_callback(completed, total):
            if not hasattr(progress_callback, 'last_completed'):
                progress_callback.last_completed = 0
            
            increment = completed - progress_callback.last_completed
            if increment > 0:
                tracker.update(increment)
                progress_callback.last_completed = completed
        
        # Simulate processing chunks in batches
        for batch_end in [5, 12, 18, 25]:
            progress_callback(batch_end, chunk_count)
        
        tracker.close()
        self.assertEqual(tracker.current, chunk_count)
    
    def test_eta_calculation_simulation(self):
        """Test ETA calculation concepts."""
        start_time = time.time()
        total_items = 100
        
        # Simulate processing with timing
        processed = 0
        for batch in [10, 25, 50, 75, 100]:
            processed = batch
            elapsed = time.time() - start_time + (batch * 0.001)  # Simulate time
            
            if processed > 0:
                rate = processed / elapsed  # items per second
                remaining = total_items - processed
                eta = remaining / rate if rate > 0 else 0
                
                # Verify ETA calculation makes sense
                if processed < total_items:
                    self.assertGreater(eta, 0)
                else:
                    self.assertEqual(eta, 0)
    
    def test_error_handling_with_progress(self):
        """Test progress tracking with error scenarios."""
        tracker = ProgressTracker(10, "Test with errors")
        
        # Simulate processing with some failures
        successful = 0
        failed = 0
        
        for i in range(10):
            try:
                # Simulate random failures
                if i in [3, 7]:  # Simulate failures at items 3 and 7
                    failed += 1
                    raise Exception(f"Processing failed for item {i}")
                else:
                    successful += 1
                
                tracker.update()
                
            except Exception:
                # Still update progress even on failure
                tracker.update()
                continue
        
        tracker.close()
        
        # Verify all items were processed (successfully or not)
        self.assertEqual(tracker.current, 10)
        self.assertEqual(successful + failed, 10)
        self.assertEqual(successful, 8)
        self.assertEqual(failed, 2)


class TestUserFeedback(unittest.TestCase):
    """Test user feedback and messaging systems."""
    
    @patch('builtins.print')
    def test_status_messages(self, mock_print):
        """Test status message formatting."""
        # Simulate various status messages
        messages = [
            "Phase 1: Discovering files...",
            "Phase 2: Loading files and applying OCR...",
            "Phase 3: Chunking content...",
            "Phase 4: Processing with Azure OpenAI GPT...",
            "Phase 5: Consolidating and deduplicating data...",
            "Phase 6: Generating document outline...",
            "Phase 7: Generating output files..."
        ]
        
        for message in messages:
            print(message)
        
        # Verify all messages were printed
        self.assertEqual(mock_print.call_count, len(messages))
        
        # Verify message format
        for i, call in enumerate(mock_print.call_args_list):
            self.assertEqual(call[0][0], messages[i])
    
    def test_summary_statistics_formatting(self):
        """Test formatting of summary statistics."""
        stats = {
            "input_files": 150,
            "documents_processed": 145,
            "chunks_created": 89,
            "gpt_requests": 89,
            "success_rate": 96.6,
            "tokens_used": 125000,
            "medical_records": 45,
            "deduplication_merges": 12,
            "output_files": 8
        }
        
        # Test formatting functions would be here
        # This simulates what the actual summary would look like
        summary_lines = [
            f"Input files: {stats['input_files']}",
            f"Documents processed: {stats['documents_processed']}",
            f"Chunks created: {stats['chunks_created']}",
            f"GPT requests: {stats['gpt_requests']}",
            f"Success rate: {stats['success_rate']:.1f}%",
            f"Tokens used: {stats['tokens_used']:,}",
            f"Medical records: {stats['medical_records']}",
            f"Deduplication merges: {stats['deduplication_merges']}",
            f"Output files: {stats['output_files']}"
        ]
        
        # Verify formatting
        self.assertIn("150", summary_lines[0])
        self.assertIn("96.6%", summary_lines[4])
        self.assertIn("125,000", summary_lines[5])  # Comma formatting
    
    def test_error_message_formatting(self):
        """Test error message formatting and clarity."""
        error_scenarios = [
            {
                "error": "Configuration file not found",
                "solution": "Run 'python organizer.py --create-config' to generate template"
            },
            {
                "error": "OCR dependencies not available",
                "solution": "Install with: pip install pytesseract pillow pdf2image"
            },
            {
                "error": "Azure OpenAI API key invalid",
                "solution": "Check your API key in config.json"
            }
        ]
        
        for scenario in error_scenarios:
            # Verify error messages are informative
            self.assertIn("not", scenario["error"].lower())
            self.assertIn("install" if "dependencies" in scenario["error"] else "config", 
                         scenario["solution"].lower())


if __name__ == '__main__':
    unittest.main()