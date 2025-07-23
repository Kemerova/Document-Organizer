"""
Unit tests for data models.
"""

import unittest
import tempfile
import os
from datetime import datetime
from pathlib import Path

from utils.models import (
    DocumentContent,
    GPTResponse,
    MedicalRecord,
    LifeHistoryRecord,
    ProcessingMetadata,
    ChunkMetadata,
    save_json_backup,
    load_json_backup
)


class TestDocumentContent(unittest.TestCase):
    """Test cases for DocumentContent model."""
    
    def test_valid_document_content(self):
        """Test valid document content creation and validation."""
        doc = DocumentContent(
            filename="test.txt",
            content="Test content",
            page_numbers=[1, 2],
            file_type="txt",
            ocr_applied=False,
            extraction_confidence=0.95
        )
        
        self.assertTrue(doc.validate())
        self.assertEqual(doc.filename, "test.txt")
        self.assertEqual(doc.content, "Test content")
        self.assertEqual(doc.page_numbers, [1, 2])
    
    def test_invalid_document_content(self):
        """Test invalid document content validation."""
        # Empty filename
        doc = DocumentContent(filename="", content="Test")
        self.assertFalse(doc.validate())
        
        # Invalid confidence score
        doc = DocumentContent(filename="test.txt", content="Test", extraction_confidence=1.5)
        self.assertFalse(doc.validate())
        
        # Non-string content
        doc = DocumentContent(filename="test.txt", content=123)
        self.assertFalse(doc.validate())
    
    def test_document_content_serialization(self):
        """Test document content to_dict method."""
        doc = DocumentContent(
            filename="test.txt",
            content="Test content",
            page_numbers=[1, 2],
            file_type="txt"
        )
        
        data = doc.to_dict()
        self.assertEqual(data['filename'], "test.txt")
        self.assertEqual(data['content'], "Test content")
        self.assertEqual(data['page_numbers'], [1, 2])
        self.assertEqual(data['file_type'], "txt")


class TestGPTResponse(unittest.TestCase):
    """Test cases for GPTResponse model."""
    
    def test_valid_gpt_response(self):
        """Test valid GPT response creation and validation."""
        response = GPTResponse(
            chunk_id="chunk_001",
            structured_data={"key": "value"},
            summary="Test summary",
            confidence_score=0.8,
            source_references=["file1.txt", "file2.txt"],
            processing_time=1.5
        )
        
        self.assertTrue(response.validate())
        self.assertEqual(response.chunk_id, "chunk_001")
        self.assertEqual(response.structured_data, {"key": "value"})
    
    def test_invalid_gpt_response(self):
        """Test invalid GPT response validation."""
        # Empty chunk_id
        response = GPTResponse(chunk_id="", structured_data={})
        self.assertFalse(response.validate())
        
        # Invalid confidence score
        response = GPTResponse(chunk_id="test", structured_data={}, confidence_score=-0.1)
        self.assertFalse(response.validate())
    
    def test_gpt_response_serialization(self):
        """Test GPT response to_dict method."""
        response = GPTResponse(
            chunk_id="chunk_001",
            structured_data={"key": "value"},
            confidence_score=0.8
        )
        
        data = response.to_dict()
        self.assertEqual(data['chunk_id'], "chunk_001")
        self.assertEqual(data['structured_data'], {"key": "value"})
        self.assertEqual(data['confidence_score'], 0.8)


class TestMedicalRecord(unittest.TestCase):
    """Test cases for MedicalRecord model."""
    
    def test_valid_medical_record(self):
        """Test valid medical record creation and validation."""
        visit_date = datetime(2024, 1, 15)
        record = MedicalRecord(
            condition="Hypertension",
            visit_dates=[visit_date],
            medications=["Lisinopril", "Amlodipine"],
            physician="Dr. Smith",
            notes="Blood pressure controlled",
            source_files=["medical_record_1.pdf"],
            page_references=[1, 2],
            confidence_score=0.9
        )
        
        self.assertTrue(record.validate())
        self.assertEqual(record.condition, "Hypertension")
        self.assertEqual(len(record.visit_dates), 1)
        self.assertEqual(record.visit_dates[0], visit_date)
    
    def test_invalid_medical_record(self):
        """Test invalid medical record validation."""
        # Empty condition
        record = MedicalRecord(condition="")
        self.assertFalse(record.validate())
        
        # Invalid visit date
        record = MedicalRecord(condition="Test", visit_dates=["not_a_date"])
        self.assertFalse(record.validate())
    
    def test_medical_record_serialization(self):
        """Test medical record serialization and deserialization."""
        visit_date = datetime(2024, 1, 15)
        record = MedicalRecord(
            condition="Hypertension",
            visit_dates=[visit_date],
            medications=["Lisinopril"],
            physician="Dr. Smith"
        )
        
        data = record.to_dict()
        self.assertEqual(data['condition'], "Hypertension")
        self.assertEqual(data['visit_dates'], [visit_date.isoformat()])
        self.assertEqual(data['medications'], ["Lisinopril"])
        
        # Test deserialization
        restored_record = MedicalRecord.from_dict(data)
        self.assertEqual(restored_record.condition, "Hypertension")
        self.assertEqual(len(restored_record.visit_dates), 1)
        self.assertEqual(restored_record.visit_dates[0], visit_date)


class TestLifeHistoryRecord(unittest.TestCase):
    """Test cases for LifeHistoryRecord model."""
    
    def test_valid_life_history_record(self):
        """Test valid life history record creation and validation."""
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2023, 12, 31)
        record = LifeHistoryRecord(
            role="Software Engineer",
            start_date=start_date,
            end_date=end_date,
            location="San Francisco, CA",
            key_achievements=["Led team of 5", "Increased performance by 40%"],
            source_files=["resume.pdf"],
            page_references=[1],
            confidence_score=0.85
        )
        
        self.assertTrue(record.validate())
        self.assertEqual(record.role, "Software Engineer")
        self.assertEqual(record.start_date, start_date)
        self.assertEqual(record.end_date, end_date)
    
    def test_invalid_life_history_record(self):
        """Test invalid life history record validation."""
        # Empty role
        record = LifeHistoryRecord(role="")
        self.assertFalse(record.validate())
        
        # End date before start date
        start_date = datetime(2023, 1, 1)
        end_date = datetime(2022, 1, 1)
        record = LifeHistoryRecord(
            role="Test Role",
            start_date=start_date,
            end_date=end_date
        )
        self.assertFalse(record.validate())
    
    def test_life_history_record_serialization(self):
        """Test life history record serialization and deserialization."""
        start_date = datetime(2020, 1, 1)
        end_date = datetime(2023, 12, 31)
        record = LifeHistoryRecord(
            role="Software Engineer",
            start_date=start_date,
            end_date=end_date,
            location="San Francisco, CA",
            key_achievements=["Achievement 1", "Achievement 2"]
        )
        
        data = record.to_dict()
        self.assertEqual(data['role'], "Software Engineer")
        self.assertEqual(data['start_date'], start_date.isoformat())
        self.assertEqual(data['end_date'], end_date.isoformat())
        
        # Test deserialization
        restored_record = LifeHistoryRecord.from_dict(data)
        self.assertEqual(restored_record.role, "Software Engineer")
        self.assertEqual(restored_record.start_date, start_date)
        self.assertEqual(restored_record.end_date, end_date)


class TestProcessingMetadata(unittest.TestCase):
    """Test cases for ProcessingMetadata model."""
    
    def test_valid_processing_metadata(self):
        """Test valid processing metadata creation and validation."""
        metadata = ProcessingMetadata(
            total_files=100,
            processed_files=95,
            failed_files=["file1.txt", "file2.txt"],
            total_tokens=50000,
            api_calls_made=25,
            processing_time=120.5
        )
        
        self.assertTrue(metadata.validate())
        self.assertEqual(metadata.total_files, 100)
        self.assertEqual(metadata.processed_files, 95)
    
    def test_invalid_processing_metadata(self):
        """Test invalid processing metadata validation."""
        # Processed files > total files
        metadata = ProcessingMetadata(total_files=10, processed_files=15)
        self.assertFalse(metadata.validate())
        
        # Negative values
        metadata = ProcessingMetadata(total_files=-1)
        self.assertFalse(metadata.validate())
    
    def test_processing_metadata_calculations(self):
        """Test processing metadata calculation methods."""
        metadata = ProcessingMetadata(
            total_files=100,
            processed_files=90,
            failed_files=["file1.txt", "file2.txt"],
            processing_time=60.0
        )
        
        # Test success rate
        success_rate = metadata.get_success_rate()
        self.assertEqual(success_rate, 0.88)  # (90 - 2) / 100
        
        # Test processing speed
        speed = metadata.get_processing_speed()
        self.assertEqual(speed, 1.5)  # 90 / 60
        
        # Test add failed file
        metadata.add_failed_file("file3.txt")
        self.assertIn("file3.txt", metadata.failed_files)
        
        # Test increment processed
        metadata.increment_processed()
        self.assertEqual(metadata.processed_files, 91)


class TestChunkMetadata(unittest.TestCase):
    """Test cases for ChunkMetadata model."""
    
    def test_valid_chunk_metadata(self):
        """Test valid chunk metadata creation and validation."""
        chunk = ChunkMetadata(
            chunk_id="chunk_001",
            source_file="document.pdf",
            page_numbers=[1, 2, 3],
            token_count=1500,
            chunk_index=0,
            total_chunks=5
        )
        
        self.assertTrue(chunk.validate())
        self.assertEqual(chunk.chunk_id, "chunk_001")
        self.assertEqual(chunk.token_count, 1500)
    
    def test_invalid_chunk_metadata(self):
        """Test invalid chunk metadata validation."""
        # Empty chunk_id
        chunk = ChunkMetadata(chunk_id="", source_file="test.txt")
        self.assertFalse(chunk.validate())
        
        # Chunk index >= total chunks
        chunk = ChunkMetadata(
            chunk_id="test",
            source_file="test.txt",
            chunk_index=5,
            total_chunks=5
        )
        self.assertFalse(chunk.validate())


class TestJSONBackup(unittest.TestCase):
    """Test cases for JSON backup functionality."""
    
    def test_save_and_load_json_backup(self):
        """Test saving and loading JSON backup files."""
        test_data = {
            "test_key": "test_value",
            "test_number": 42,
            "test_list": [1, 2, 3],
            "test_datetime": datetime(2024, 1, 15, 10, 30, 0)
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            # Test saving
            save_json_backup(test_data, temp_path)
            self.assertTrue(Path(temp_path).exists())
            
            # Test loading
            loaded_data = load_json_backup(temp_path)
            self.assertEqual(loaded_data['test_key'], "test_value")
            self.assertEqual(loaded_data['test_number'], 42)
            self.assertEqual(loaded_data['test_list'], [1, 2, 3])
            # Datetime should be serialized as ISO string
            self.assertEqual(loaded_data['test_datetime'], "2024-01-15T10:30:00")
            
        finally:
            if Path(temp_path).exists():
                os.unlink(temp_path)
    
    def test_save_json_backup_with_models(self):
        """Test saving JSON backup with model objects."""
        doc = DocumentContent(
            filename="test.txt",
            content="Test content",
            page_numbers=[1, 2]
        )
        
        test_data = {
            "document": doc,
            "timestamp": datetime.now()
        }
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            temp_path = f.name
        
        try:
            save_json_backup(test_data, temp_path)
            loaded_data = load_json_backup(temp_path)
            
            # Check that the document was serialized properly
            self.assertEqual(loaded_data['document']['filename'], "test.txt")
            self.assertEqual(loaded_data['document']['content'], "Test content")
            
        finally:
            if Path(temp_path).exists():
                os.unlink(temp_path)


if __name__ == '__main__':
    unittest.main()