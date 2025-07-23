"""
Unit tests for file loader functionality.
"""

import unittest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

from utils.file_loader import FileLoader, FileLoadError, SUPPORTED_EXTENSIONS
from utils.models import DocumentContent


class TestFileLoader(unittest.TestCase):
    """Test cases for FileLoader class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.loader = FileLoader()
        self.temp_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temp directory
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_temp_file(self, filename: str, content: str = "Test content") -> str:
        """Create a temporary file with given content."""
        file_path = Path(self.temp_dir) / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(file_path)
    
    def test_discover_files_single_file(self):
        """Test file discovery with a single file."""
        # Create test file
        test_file = self.create_temp_file("test.txt")
        
        files = self.loader.discover_files(test_file, recursive=False)
        self.assertEqual(len(files), 1)
        self.assertIn(test_file, files)
    
    def test_discover_files_directory(self):
        """Test file discovery in a directory."""
        # Create test files
        self.create_temp_file("file1.txt")
        self.create_temp_file("file2.docx")
        self.create_temp_file("file3.pdf")
        self.create_temp_file("file4.jpg")
        self.create_temp_file("unsupported.xyz")  # Should be ignored
        
        files = self.loader.discover_files(self.temp_dir)
        self.assertEqual(len(files), 4)  # Only supported files
        
        # Check that all supported extensions are found
        extensions = {Path(f).suffix.lower() for f in files}
        expected_extensions = {'.txt', '.docx', '.pdf', '.jpg'}
        self.assertEqual(extensions, expected_extensions)
    
    def test_discover_files_recursive(self):
        """Test recursive file discovery."""
        # Create files in subdirectories
        self.create_temp_file("root.txt")
        self.create_temp_file("subdir/sub1.txt")
        self.create_temp_file("subdir/nested/sub2.txt")
        
        # Test recursive
        files = self.loader.discover_files(self.temp_dir, recursive=True)
        self.assertEqual(len(files), 3)
        
        # Test non-recursive
        files = self.loader.discover_files(self.temp_dir, recursive=False)
        self.assertEqual(len(files), 1)  # Only root.txt
    
    def test_discover_files_nonexistent_path(self):
        """Test file discovery with nonexistent path."""
        with self.assertRaises(FileLoadError):
            self.loader.discover_files("/nonexistent/path")
    
    def test_load_text_file(self):
        """Test loading a text file."""
        content = "This is test content\\nWith multiple lines"
        test_file = self.create_temp_file("test.txt", content)
        
        doc_content = self.loader.load_text_file(test_file)
        
        self.assertIsInstance(doc_content, DocumentContent)
        self.assertEqual(doc_content.filename, test_file)
        self.assertEqual(doc_content.content, content)
        self.assertEqual(doc_content.file_type, "txt")
        self.assertFalse(doc_content.ocr_applied)
        self.assertEqual(doc_content.page_numbers, [1])
    
    def test_load_text_file_encoding_detection(self):
        """Test text file loading with encoding detection."""
        # Create file with specific encoding
        test_file = Path(self.temp_dir) / "encoded.txt"
        content = "Test content with special chars: àáâãäå"
        
        with open(test_file, 'w', encoding='latin-1') as f:
            f.write(content)
        
        doc_content = self.loader.load_text_file(str(test_file))
        self.assertIsInstance(doc_content, DocumentContent)
        # Content should be readable regardless of original encoding
        self.assertIn("Test content", doc_content.content)
    
    @patch('docx.Document')
    def test_load_docx_file(self, mock_docx):
        """Test loading a DOCX file."""
        # Mock docx.Document
        mock_doc = MagicMock()
        mock_paragraph1 = MagicMock()
        mock_paragraph1.text = "First paragraph"
        mock_paragraph2 = MagicMock()
        mock_paragraph2.text = "Second paragraph"
        
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_doc.tables = []  # No tables
        mock_docx.return_value = mock_doc
        
        test_file = self.create_temp_file("test.docx")
        doc_content = self.loader.load_docx_file(test_file)
        
        self.assertIsInstance(doc_content, DocumentContent)
        self.assertEqual(doc_content.filename, test_file)
        self.assertIn("First paragraph", doc_content.content)
        self.assertIn("Second paragraph", doc_content.content)
        self.assertEqual(doc_content.file_type, "docx")
        self.assertFalse(doc_content.ocr_applied)
        self.assertEqual(doc_content.extraction_confidence, 0.95)
    
    @patch('PyPDF2.PdfReader')
    def test_load_pdf_file(self, mock_pdf_reader):
        """Test loading a PDF file."""
        # Mock PDF reader
        mock_reader = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2 content"
        
        mock_reader.pages = [mock_page1, mock_page2]
        mock_pdf_reader.return_value = mock_reader
        
        test_file = self.create_temp_file("test.pdf")
        
        with patch('builtins.open', unittest.mock.mock_open()):
            doc_content = self.loader.load_pdf_file(test_file)
        
        self.assertIsInstance(doc_content, DocumentContent)
        self.assertEqual(doc_content.filename, test_file)
        self.assertIn("Page 1 content", doc_content.content)
        self.assertIn("Page 2 content", doc_content.content)
        self.assertEqual(doc_content.file_type, "pdf")
        self.assertEqual(doc_content.page_numbers, [1, 2])
        self.assertFalse(doc_content.ocr_applied)
    
    def test_load_file_dispatch(self):
        """Test that load_file dispatches to correct loader based on extension."""
        # Test text file
        test_txt = self.create_temp_file("test.txt", "Text content")
        doc_content = self.loader.load_file(test_txt)
        self.assertEqual(doc_content.file_type, "txt")
        
        # Test image file (should return empty content for OCR processing)
        test_jpg = self.create_temp_file("test.jpg", "fake image content")
        doc_content = self.loader.load_file(test_jpg)
        self.assertEqual(doc_content.file_type, "jpg")
        self.assertEqual(doc_content.content, "")  # Empty, waiting for OCR
        self.assertFalse(doc_content.ocr_applied)
    
    def test_load_file_nonexistent(self):
        """Test loading a nonexistent file."""
        with self.assertRaises(FileLoadError):
            self.loader.load_file("/nonexistent/file.txt")
    
    def test_load_file_unsupported_extension(self):
        """Test loading a file with unsupported extension."""
        test_file = self.create_temp_file("test.xyz", "content")
        
        with self.assertRaises(FileLoadError):
            self.loader.load_file(test_file)
    
    def test_get_file_info(self):
        """Test getting file information."""
        test_file = self.create_temp_file("test.txt", "Test content")
        
        info = self.loader.get_file_info(test_file)
        
        self.assertEqual(info['filename'], "test.txt")
        self.assertEqual(info['full_path'], test_file)
        self.assertEqual(info['extension'], '.txt')
        self.assertTrue(info['is_supported'])
        self.assertGreater(info['size_bytes'], 0)
        self.assertGreaterEqual(info['size_mb'], 0)  # Small files may be 0.0 MB
    
    def test_get_file_info_nonexistent(self):
        """Test getting info for nonexistent file."""
        info = self.loader.get_file_info("/nonexistent/file.txt")
        self.assertEqual(info, {})
    
    def test_batch_load_files(self):
        """Test batch loading of files."""
        # Create test files
        file1 = self.create_temp_file("file1.txt", "Content 1")
        file2 = self.create_temp_file("file2.txt", "Content 2")
        file3 = "/nonexistent/file3.txt"  # This should be skipped
        
        files = [file1, file2, file3]
        results = list(self.loader.batch_load_files(files))
        
        # Should get 2 results (file3 should be skipped due to error)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].content, "Content 1")
        self.assertEqual(results[1].content, "Content 2")
    
    def test_validate_input_path(self):
        """Test input path validation."""
        # Valid path with supported files
        self.create_temp_file("test.txt")
        self.assertTrue(self.loader.validate_input_path(self.temp_dir))
        
        # Invalid path
        self.assertFalse(self.loader.validate_input_path("/nonexistent/path"))
        
        # Empty directory
        empty_dir = tempfile.mkdtemp()
        try:
            self.assertFalse(self.loader.validate_input_path(empty_dir))
        finally:
            os.rmdir(empty_dir)
    
    def test_get_file_statistics(self):
        """Test file statistics calculation."""
        # Create test files of different types and sizes
        file1 = self.create_temp_file("small.txt", "x")  # Very small
        file2 = self.create_temp_file("large.txt", "large content " * 1000)  # Much larger
        file3 = self.create_temp_file("doc.docx", "medium content")
        
        files = [file1, file2, file3]
        stats = self.loader.get_file_statistics(files)
        
        self.assertEqual(stats['total_files'], 3)
        self.assertEqual(stats['by_extension']['.txt'], 2)
        self.assertEqual(stats['by_extension']['.docx'], 1)
        self.assertGreaterEqual(stats['total_size_mb'], 0)  # May be 0.0 for small files
        self.assertIsNotNone(stats['largest_file'])
        self.assertIsNotNone(stats['smallest_file'])
        
        # Largest should be the file with repeated content
        self.assertEqual(stats['largest_file'][0], file2)
        # Smallest should be the single character file
        self.assertEqual(stats['smallest_file'][0], file1)
    
    def test_supported_extensions(self):
        """Test that all expected extensions are supported."""
        expected_extensions = {'.txt', '.docx', '.pdf', '.jpg', '.jpeg', '.png'}
        self.assertEqual(SUPPORTED_EXTENSIONS, expected_extensions)
        self.assertEqual(self.loader.supported_extensions, expected_extensions)


if __name__ == '__main__':
    unittest.main()