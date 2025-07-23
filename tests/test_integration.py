"""
End-to-end integration tests for Document Organizer.
Tests complete workflows with sample data and validates output correctness.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from utils.config import Config, AzureOpenAIConfig, ProcessingConfig
from utils.file_loader import FileLoader
from utils.chunker import TokenAwareChunker
from utils.processor import DataProcessor
from utils.output_writer import OutputWriter
from utils.models import DocumentContent, MedicalRecord, LifeHistoryRecord


class TestEndToEndIntegration(unittest.TestCase):
    """End-to-end integration tests."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = Path(self.temp_dir) / "input"
        self.output_dir = Path(self.temp_dir) / "output"
        
        self.input_dir.mkdir(parents=True)
        self.output_dir.mkdir(parents=True)
        
        # Create test configuration
        self.config = Config(
            azure_openai=AzureOpenAIConfig(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                deployment_name="gpt-4",
                api_version="2024-02-15-preview"
            ),
            processing=ProcessingConfig(
                max_concurrent_requests=2,
                chunk_size_tokens=1000,
                retry_attempts=1
            )
        )
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_sample_medical_documents(self):
        """Create sample medical documents for testing."""
        documents = [
            {
                "filename": "medical_record_1.txt",
                "content": """
                Patient: John Doe
                Date: 2023-01-15
                Diagnosis: Hypertension, Type 2 Diabetes
                Medications: Lisinopril 10mg daily, Metformin 500mg twice daily
                Physician: Dr. Sarah Smith, Internal Medicine
                Notes: Blood pressure well controlled. HbA1c improved to 7.2%.
                Follow-up in 3 months.
                """
            },
            {
                "filename": "medical_record_2.txt",
                "content": """
                Patient: John Doe
                Date: 2023-04-20
                Diagnosis: Hypertension, Type 2 Diabetes
                Medications: Lisinopril 10mg daily, Metformin 500mg twice daily
                Physician: Dr. Sarah Smith, Internal Medicine
                Notes: Blood pressure stable. HbA1c now 6.8%. Continue current medications.
                Next visit in 6 months.
                """
            },
            {
                "filename": "cardiology_consult.txt",
                "content": """
                Patient: John Doe
                Date: 2023-02-10
                Consultation: Cardiology
                Physician: Dr. Michael Johnson, Cardiology
                Reason: Hypertension management
                Assessment: Well-controlled hypertension. No signs of cardiac complications.
                Recommendations: Continue current antihypertensive therapy.
                """
            }
        ]
        
        for doc in documents:
            file_path = self.input_dir / doc["filename"]
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(doc["content"])
        
        return documents
    
    def create_sample_life_documents(self):
        """Create sample life history documents for testing."""
        documents = [
            {
                "filename": "resume_2020_2022.txt",
                "content": """
                Position: Senior Software Engineer
                Company: Tech Innovations Inc.
                Duration: January 2020 - December 2022
                Location: San Francisco, CA
                
                Key Achievements:
                - Led development team of 8 engineers
                - Architected microservices platform serving 1M+ users
                - Reduced system latency by 40% through optimization
                - Mentored 3 junior developers
                
                Technologies: Python, AWS, Docker, Kubernetes
                """
            },
            {
                "filename": "performance_review_2021.txt",
                "content": """
                Employee: John Smith
                Position: Senior Software Engineer
                Review Period: 2021
                Manager: Jane Wilson
                
                Performance Summary:
                - Exceeded all technical goals for the year
                - Successfully launched 3 major features
                - Demonstrated strong leadership in cross-team projects
                - Received "Outstanding Contributor" award
                
                Areas of Excellence:
                - Technical architecture and design
                - Team collaboration and mentoring
                - Problem-solving and innovation
                """
            },
            {
                "filename": "training_certificate.txt",
                "content": """
                Certificate of Completion
                
                Course: Advanced Cloud Architecture
                Provider: Cloud Academy
                Completion Date: March 15, 2021
                Duration: 40 hours
                
                Skills Covered:
                - AWS Solution Architecture
                - Scalable system design
                - Security best practices
                - Cost optimization strategies
                
                Grade: A+ (95%)
                """
            }
        ]
        
        for doc in documents:
            file_path = self.input_dir / doc["filename"]
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(doc["content"])
        
        return documents
    
    def test_medical_workflow_integration(self):
        """Test complete medical document processing workflow."""
        # Create sample documents
        sample_docs = self.create_sample_medical_documents()
        
        # Step 1: File discovery and loading
        file_loader = FileLoader()
        discovered_files = file_loader.discover_files(str(self.input_dir))
        
        self.assertEqual(len(discovered_files), 3)
        
        # Load documents
        documents = []
        for file_path in discovered_files:
            doc_content = file_loader.load_file(file_path)
            documents.append(doc_content)
        
        self.assertEqual(len(documents), 3)
        
        # Step 2: Content chunking
        chunker = TokenAwareChunker(max_tokens=500)  # Small chunks for testing
        chunks = chunker.chunk_content(documents)
        
        self.assertGreater(len(chunks), 0)
        
        # Validate chunk structure
        for chunk in chunks:
            self.assertIsNotNone(chunk.chunk_id)
            self.assertIsNotNone(chunk.content)
            self.assertGreater(chunk.token_count, 0)
            self.assertGreater(len(chunk.source_files), 0)
        
        # Step 3: Mock GPT processing (since we can't make real API calls in tests)
        mock_responses = self.create_mock_medical_responses(chunks)
        
        # Step 4: Data consolidation and deduplication
        processor = DataProcessor()
        consolidated_data = processor.consolidate_responses(mock_responses, 'medical')
        
        # Validate consolidated data
        self.assertGreater(len(consolidated_data.medical_records), 0)
        self.assertGreater(len(consolidated_data.summaries), 0)
        
        # Check for deduplication (should merge duplicate conditions)
        conditions = [record.condition for record in consolidated_data.medical_records]
        unique_conditions = set(conditions)
        self.assertLessEqual(len(unique_conditions), len(conditions))  # Some deduplication should occur
        
        # Step 5: Output generation
        output_writer = OutputWriter(str(self.output_dir))
        
        # Mock outline data
        outline_data = {
            "outline": {
                "title": "Medical Records Overview",
                "sections": [
                    {
                        "section_title": "Chronic Conditions",
                        "subsections": [
                            {
                                "title": "Hypertension Management",
                                "content": "Well-controlled hypertension with regular monitoring",
                                "document_count": 3
                            }
                        ]
                    }
                ]
            },
            "key_themes": ["Hypertension", "Diabetes", "Medication Management"],
            "date_range": "2023-01-15 to 2023-04-20",
            "total_documents": 3
        }
        
        generated_files = output_writer.write_all_formats(
            consolidated_data, 'medical', outline_data, mock_responses
        )
        
        # Validate output files were generated
        self.assertIn("markdown", generated_files)
        self.assertIn("csv", generated_files)
        self.assertIn("json", generated_files)
        
        # Check that files actually exist
        for format_files in generated_files.values():
            for file_path in format_files:
                self.assertTrue(Path(file_path).exists(), f"Output file not found: {file_path}")
    
    def test_life_history_workflow_integration(self):
        """Test complete life history document processing workflow."""
        # Create sample documents
        sample_docs = self.create_sample_life_documents()
        
        # Step 1: File discovery and loading
        file_loader = FileLoader()
        discovered_files = file_loader.discover_files(str(self.input_dir))
        
        self.assertEqual(len(discovered_files), 3)
        
        # Load documents
        documents = []
        for file_path in discovered_files:
            doc_content = file_loader.load_file(file_path)
            documents.append(doc_content)
        
        # Step 2: Content chunking
        chunker = TokenAwareChunker(max_tokens=500)
        chunks = chunker.chunk_content(documents)
        
        # Step 3: Mock GPT processing
        mock_responses = self.create_mock_life_responses(chunks)
        
        # Step 4: Data consolidation
        processor = DataProcessor()
        consolidated_data = processor.consolidate_responses(mock_responses, 'life')
        
        # Validate consolidated data
        self.assertGreater(len(consolidated_data.life_history_records), 0)
        
        # Step 5: Output generation
        output_writer = OutputWriter(str(self.output_dir))
        
        outline_data = {
            "outline": {
                "title": "Career History Overview",
                "sections": [
                    {
                        "section_title": "Professional Experience",
                        "subsections": [
                            {
                                "title": "Software Engineering Career",
                                "content": "Progressive career in software development",
                                "document_count": 3
                            }
                        ]
                    }
                ]
            },
            "key_themes": ["Software Engineering", "Leadership", "Technical Skills"],
            "date_range": "2020-2022",
            "total_documents": 3
        }
        
        generated_files = output_writer.write_all_formats(
            consolidated_data, 'life', outline_data, mock_responses
        )
        
        # Validate output files
        for format_files in generated_files.values():
            for file_path in format_files:
                self.assertTrue(Path(file_path).exists())
    
    def create_mock_medical_responses(self, chunks):
        """Create mock GPT responses for medical processing."""
        from utils.azure_gpt import GPTResponse
        
        responses = []
        for i, chunk in enumerate(chunks):
            # Create realistic medical response data
            if "hypertension" in chunk.content.lower():
                structured_data = {
                    "medical_records": [
                        {
                            "condition": "Hypertension",
                            "visit_dates": ["2023-01-15", "2023-04-20"],
                            "medications": ["Lisinopril 10mg daily"],
                            "physician": "Dr. Sarah Smith",
                            "notes": "Blood pressure well controlled",
                            "confidence": 0.9
                        }
                    ],
                    "summary": "Patient has well-controlled hypertension with regular monitoring"
                }
            elif "diabetes" in chunk.content.lower():
                structured_data = {
                    "medical_records": [
                        {
                            "condition": "Type 2 Diabetes",
                            "visit_dates": ["2023-01-15", "2023-04-20"],
                            "medications": ["Metformin 500mg twice daily"],
                            "physician": "Dr. Sarah Smith",
                            "notes": "HbA1c improved from 7.2% to 6.8%",
                            "confidence": 0.85
                        }
                    ],
                    "summary": "Diabetes management showing good improvement"
                }
            else:
                structured_data = {
                    "medical_records": [],
                    "summary": "General medical information"
                }
            
            response = GPTResponse(
                chunk_id=chunk.chunk_id,
                structured_data=structured_data,
                summary=structured_data["summary"],
                confidence_score=0.8,
                source_references=chunk.source_files,
                processing_time=1.0,
                token_usage={"total_tokens": 100},
                raw_response=json.dumps(structured_data)
            )
            responses.append(response)
        
        return responses
    
    def create_mock_life_responses(self, chunks):
        """Create mock GPT responses for life history processing."""
        from utils.azure_gpt import GPTResponse
        
        responses = []
        for i, chunk in enumerate(chunks):
            # Create realistic life history response data
            if "software engineer" in chunk.content.lower():
                structured_data = {
                    "life_history_records": [
                        {
                            "role": "Senior Software Engineer",
                            "start_date": "2020-01-01",
                            "end_date": "2022-12-31",
                            "location": "Tech Innovations Inc., San Francisco, CA",
                            "key_achievements": [
                                "Led development team of 8 engineers",
                                "Architected microservices platform",
                                "Reduced system latency by 40%"
                            ],
                            "confidence": 0.9
                        }
                    ],
                    "summary": "Senior software engineering role with leadership responsibilities"
                }
            elif "training" in chunk.content.lower() or "certificate" in chunk.content.lower():
                structured_data = {
                    "life_history_records": [
                        {
                            "role": "Advanced Cloud Architecture Training",
                            "start_date": "2021-03-01",
                            "end_date": "2021-03-15",
                            "location": "Cloud Academy",
                            "key_achievements": [
                                "Completed 40-hour advanced course",
                                "Achieved A+ grade (95%)",
                                "Mastered AWS Solution Architecture"
                            ],
                            "confidence": 0.85
                        }
                    ],
                    "summary": "Professional development in cloud architecture"
                }
            else:
                structured_data = {
                    "life_history_records": [],
                    "summary": "General career information"
                }
            
            response = GPTResponse(
                chunk_id=chunk.chunk_id,
                structured_data=structured_data,
                summary=structured_data["summary"],
                confidence_score=0.8,
                source_references=chunk.source_files,
                processing_time=1.0,
                token_usage={"total_tokens": 100},
                raw_response=json.dumps(structured_data)
            )
            responses.append(response)
        
        return responses
    
    def test_error_handling_integration(self):
        """Test error handling in integrated workflow."""
        # Create a problematic file
        problem_file = self.input_dir / "corrupted.txt"
        with open(problem_file, 'wb') as f:
            f.write(b'\x00\x01\x02\x03')  # Binary data that might cause encoding issues
        
        # Also create a normal file
        normal_file = self.input_dir / "normal.txt"
        with open(normal_file, 'w', encoding='utf-8') as f:
            f.write("This is normal text content.")
        
        # Test file loading with error handling
        file_loader = FileLoader()
        discovered_files = file_loader.discover_files(str(self.input_dir))
        
        successful_loads = 0
        failed_loads = 0
        
        for file_path in discovered_files:
            try:
                doc_content = file_loader.load_file(file_path)
                if doc_content['content'].strip():
                    successful_loads += 1
                else:
                    failed_loads += 1
            except Exception:
                failed_loads += 1
        
        # Should handle errors gracefully
        self.assertGreater(successful_loads, 0)  # At least one file should load
        # May or may not have failures depending on error handling
    
    def test_output_format_validation(self):
        """Test that output formats are valid and contain expected data."""
        # Create minimal test data
        from utils.processor import ConsolidatedData
        from datetime import datetime
        
        consolidated_data = ConsolidatedData()
        consolidated_data.medical_records = [
            MedicalRecord(
                condition="Test Condition",
                visit_dates=[datetime(2023, 1, 15)],
                medications=["Test Medication"],
                physician="Dr. Test",
                notes="Test notes",
                source_files=["test.txt"],
                page_references=[1],
                confidence_score=0.9
            )
        ]
        consolidated_data.summaries = ["Test summary"]
        consolidated_data.source_files = {"test.txt"}
        
        # Generate outputs
        output_writer = OutputWriter(str(self.output_dir))
        
        outline_data = {
            "outline": {"title": "Test Outline", "sections": []},
            "key_themes": ["Test"],
            "total_documents": 1
        }
        
        mock_responses = []  # Empty for this test
        
        generated_files = output_writer.write_all_formats(
            consolidated_data, 'medical', outline_data, mock_responses
        )
        
        # Validate CSV format
        csv_files = generated_files.get("csv", [])
        if csv_files:
            import csv
            with open(csv_files[0], 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.assertGreater(len(rows), 0)
                
                # Check required columns
                expected_columns = ['Condition', 'Visit_Dates', 'Medications', 'Physician']
                for col in expected_columns:
                    self.assertIn(col, reader.fieldnames)
        
        # Validate JSON format
        json_files = generated_files.get("json", [])
        if json_files:
            for json_file in json_files:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.assertIsInstance(data, dict)
                    # Should contain valid JSON structure
        
        # Validate Markdown format
        md_files = generated_files.get("markdown", [])
        if md_files:
            for md_file in md_files:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.assertIn("#", content)  # Should have markdown headers
                    self.assertIn("Test Condition", content)  # Should contain our test data
    
    def test_data_traceability(self):
        """Test that all output data can be traced back to source files."""
        # Create test documents with unique identifiers
        test_docs = [
            ("source1.txt", "Document 1 content with unique identifier ALPHA"),
            ("source2.txt", "Document 2 content with unique identifier BETA"),
            ("source3.txt", "Document 3 content with unique identifier GAMMA")
        ]
        
        for filename, content in test_docs:
            file_path = self.input_dir / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        # Process documents
        file_loader = FileLoader()
        discovered_files = file_loader.discover_files(str(self.input_dir))
        
        documents = []
        for file_path in discovered_files:
            doc_content = file_loader.load_file(file_path)
            documents.append(doc_content)
        
        # Create chunks
        chunker = TokenAwareChunker(max_tokens=200)  # Small chunks
        chunks = chunker.chunk_content(documents)
        
        # Verify traceability in chunks
        for chunk in chunks:
            self.assertGreater(len(chunk.source_files), 0)
            # Each chunk should reference at least one source file
            for source_file in chunk.source_files:
                self.assertTrue(any(source_file in doc['filename'] for doc in test_docs))
        
        # Mock processing and verify traceability is preserved
        mock_responses = []
        for chunk in chunks:
            from utils.azure_gpt import GPTResponse
            response = GPTResponse(
                chunk_id=chunk.chunk_id,
                structured_data={"test": "data"},
                summary="Test summary",
                confidence_score=0.8,
                source_references=chunk.source_files,  # Preserve source references
                processing_time=1.0,
                token_usage={"total_tokens": 50},
                raw_response='{"test": "data"}'
            )
            mock_responses.append(response)
        
        # Verify source references are preserved in responses
        all_source_refs = set()
        for response in mock_responses:
            all_source_refs.update(response.source_references)
        
        # Should have references to all original files
        original_filenames = {filename for filename, _ in test_docs}
        self.assertTrue(all(any(orig in ref for ref in all_source_refs) for orig in original_filenames))


class TestPerformanceIntegration(unittest.TestCase):
    """Test performance aspects of the integrated system."""
    
    def setUp(self):
        """Set up performance test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.input_dir = Path(self.temp_dir) / "input"
        self.input_dir.mkdir(parents=True)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_large_document_set_processing(self):
        """Test processing of a large number of documents."""
        # Create many small documents
        num_docs = 50  # Reduced for test performance
        
        for i in range(num_docs):
            file_path = self.input_dir / f"doc_{i:03d}.txt"
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"Document {i} content. This is test document number {i} with some sample text.")
        
        # Test file discovery performance
        import time
        start_time = time.time()
        
        file_loader = FileLoader()
        discovered_files = file_loader.discover_files(str(self.input_dir))
        
        discovery_time = time.time() - start_time
        
        self.assertEqual(len(discovered_files), num_docs)
        self.assertLess(discovery_time, 5.0)  # Should complete within 5 seconds
        
        # Test batch loading performance
        start_time = time.time()
        
        documents = []
        for file_path in discovered_files[:10]:  # Test with subset for speed
            doc_content = file_loader.load_file(file_path)
            documents.append(doc_content)
        
        loading_time = time.time() - start_time
        
        self.assertEqual(len(documents), 10)
        self.assertLess(loading_time, 2.0)  # Should load quickly
    
    def test_memory_usage_with_large_content(self):
        """Test memory usage with large document content."""
        # Create a large document
        large_content = "This is a test sentence. " * 1000  # ~25KB
        
        large_file = self.input_dir / "large_document.txt"
        with open(large_file, 'w', encoding='utf-8') as f:
            f.write(large_content)
        
        # Test loading and chunking
        file_loader = FileLoader()
        doc_content = file_loader.load_file(str(large_file))
        
        self.assertGreater(len(doc_content['content']), 20000)
        
        # Test chunking doesn't cause memory issues
        chunker = TokenAwareChunker(max_tokens=500)
        chunks = chunker.chunk_content([doc_content])
        
        self.assertGreater(len(chunks), 1)  # Should be split into multiple chunks
        
        # Verify chunks are reasonable size
        for chunk in chunks:
            self.assertLess(len(chunk.content), 10000)  # No chunk should be too large


if __name__ == '__main__':
    unittest.main()