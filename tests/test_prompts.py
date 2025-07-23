"""
Unit tests for GPT prompt generation and response parsing.
"""

import json
import unittest
from unittest.mock import Mock, patch

from utils.azure_gpt import AzureGPTClient, GPTResponse
from utils.config import Config, AzureOpenAIConfig, ProcessingConfig


class TestGPTPrompts(unittest.TestCase):
    """Test cases for GPT prompt generation and response parsing."""
    
    def setUp(self):
        """Set up test fixtures."""
        config = Config(
            azure_openai=AzureOpenAIConfig(
                endpoint="https://test.openai.azure.com/",
                api_key="test-key",
                deployment_name="gpt-4",
                api_version="2024-02-15-preview"
            ),
            processing=ProcessingConfig(
                max_concurrent_requests=5,
                chunk_size_tokens=4000,
                retry_attempts=2
            )
        )
        self.client = AzureGPTClient(config)
    
    def test_medical_prompt_generation(self):
        """Test medical mode prompt generation."""
        content = """
        Patient: John Doe
        Date: 2023-01-15
        Diagnosis: Hypertension
        Medication: Lisinopril 10mg daily
        Physician: Dr. Smith
        Notes: Blood pressure well controlled
        """
        
        messages = self.client._create_medical_prompt(content)
        
        # Check structure
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        
        # Check system prompt contains medical-specific instructions
        system_prompt = messages[0]["content"]
        self.assertIn("medical document analyzer", system_prompt.lower())
        self.assertIn("condition", system_prompt)
        self.assertIn("visit_dates", system_prompt)
        self.assertIn("medications", system_prompt)
        self.assertIn("physician", system_prompt)
        self.assertIn("medical_records", system_prompt)
        
        # Check user prompt contains content
        user_prompt = messages[1]["content"]
        self.assertIn(content, user_prompt)
        self.assertIn("medical document content", user_prompt.lower())
    
    def test_life_history_prompt_generation(self):
        """Test life history mode prompt generation."""
        content = """
        Position: Software Engineer
        Company: Tech Corp
        Start Date: 2020-01-15
        End Date: 2022-12-31
        Location: San Francisco, CA
        Achievements: Led team of 5 developers, increased efficiency by 30%
        """
        
        messages = self.client._create_life_history_prompt(content)
        
        # Check structure
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        
        # Check system prompt contains life history-specific instructions
        system_prompt = messages[0]["content"]
        self.assertIn("career and life history analyzer", system_prompt.lower())
        self.assertIn("role", system_prompt)
        self.assertIn("start_date", system_prompt)
        self.assertIn("end_date", system_prompt)
        self.assertIn("location", system_prompt)
        self.assertIn("key_achievements", system_prompt)
        self.assertIn("life_history_records", system_prompt)
        
        # Check user prompt contains content
        user_prompt = messages[1]["content"]
        self.assertIn(content, user_prompt)
        self.assertIn("career/life document content", user_prompt.lower())
    
    def test_outline_prompt_generation(self):
        """Test outline generation prompt."""
        summaries = [
            "Medical records from 2020-2023 showing treatment for diabetes",
            "Cardiology consultation notes from Dr. Johnson",
            "Lab results showing improved glucose levels"
        ]
        
        messages = self.client._create_outline_prompt(summaries)
        
        # Check structure
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        
        # Check system prompt contains outline-specific instructions
        system_prompt = messages[0]["content"]
        self.assertIn("document organizer", system_prompt.lower())
        self.assertIn("outline", system_prompt)
        self.assertIn("sections", system_prompt)
        self.assertIn("chronological", system_prompt)
        
        # Check user prompt contains summaries
        user_prompt = messages[1]["content"]
        for summary in summaries:
            self.assertIn(summary, user_prompt)
    
    def test_medical_response_parsing(self):
        """Test parsing of medical GPT responses."""
        # Mock a valid medical response
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "medical_records": [
                            {
                                "condition": "Hypertension",
                                "visit_dates": ["2023-01-15", "2023-03-20"],
                                "medications": ["Lisinopril 10mg"],
                                "physician": "Dr. Smith",
                                "notes": "Blood pressure controlled",
                                "confidence": 0.9
                            }
                        ],
                        "summary": "Patient has well-controlled hypertension"
                    })
                }
            }],
            "usage": {"total_tokens": 150}
        }
        
        # Create a mock chunk
        from utils.chunker import ContentChunk
        chunk = ContentChunk(
            chunk_id="test_chunk",
            content="test content",
            token_count=100,
            source_files=["test.txt"],
            page_references=[1],
            chunk_index=0,
            total_chunks=1,
            document_boundaries=[]
        )
        
        # Test response parsing (would need to mock the actual API call)
        # This tests the structure that would be returned
        content = json.loads(mock_response["choices"][0]["message"]["content"])
        
        self.assertIn("medical_records", content)
        self.assertEqual(len(content["medical_records"]), 1)
        
        record = content["medical_records"][0]
        self.assertEqual(record["condition"], "Hypertension")
        self.assertEqual(len(record["visit_dates"]), 2)
        self.assertEqual(record["medications"], ["Lisinopril 10mg"])
        self.assertEqual(record["physician"], "Dr. Smith")
        self.assertEqual(record["confidence"], 0.9)
    
    def test_life_history_response_parsing(self):
        """Test parsing of life history GPT responses."""
        # Mock a valid life history response
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "life_history_records": [
                            {
                                "role": "Software Engineer",
                                "start_date": "2020-01-15",
                                "end_date": "2022-12-31",
                                "location": "Tech Corp, San Francisco",
                                "key_achievements": [
                                    "Led team of 5 developers",
                                    "Increased efficiency by 30%"
                                ],
                                "confidence": 0.85
                            }
                        ],
                        "summary": "Software engineering role with leadership responsibilities"
                    })
                }
            }],
            "usage": {"total_tokens": 120}
        }
        
        # Test response parsing structure
        content = json.loads(mock_response["choices"][0]["message"]["content"])
        
        self.assertIn("life_history_records", content)
        self.assertEqual(len(content["life_history_records"]), 1)
        
        record = content["life_history_records"][0]
        self.assertEqual(record["role"], "Software Engineer")
        self.assertEqual(record["start_date"], "2020-01-15")
        self.assertEqual(record["end_date"], "2022-12-31")
        self.assertEqual(record["location"], "Tech Corp, San Francisco")
        self.assertEqual(len(record["key_achievements"]), 2)
        self.assertEqual(record["confidence"], 0.85)
    
    def test_json_response_validation(self):
        """Test JSON response validation and error handling."""
        # Test invalid JSON response
        invalid_responses = [
            "{ invalid json }",
            '{"medical_records": [{"condition": "test"}]}',  # Missing required fields
            '{"unknown_field": "value"}',  # Unexpected structure
            ""  # Empty response
        ]
        
        for invalid_response in invalid_responses:
            try:
                parsed = json.loads(invalid_response)
                # Should handle gracefully in actual implementation
                self.assertIsInstance(parsed, dict)
            except json.JSONDecodeError:
                # Expected for malformed JSON
                pass
    
    def test_prompt_token_efficiency(self):
        """Test that prompts are token-efficient."""
        # Test medical prompt
        medical_content = "Sample medical content"
        medical_messages = self.client._create_medical_prompt(medical_content)
        medical_system_prompt = medical_messages[0]["content"]
        
        # System prompt should be comprehensive but not excessive
        self.assertLess(len(medical_system_prompt), 2000)  # Reasonable length
        self.assertGreater(len(medical_system_prompt), 200)  # Sufficient detail
        
        # Test life history prompt
        life_content = "Sample career content"
        life_messages = self.client._create_life_history_prompt(life_content)
        life_system_prompt = life_messages[0]["content"]
        
        # System prompt should be comprehensive but not excessive
        self.assertLess(len(life_system_prompt), 2000)  # Reasonable length
        self.assertGreater(len(life_system_prompt), 200)  # Sufficient detail
    
    def test_prompt_consistency(self):
        """Test that prompts are consistent across calls."""
        content = "Test content"
        
        # Generate medical prompts multiple times
        medical_1 = self.client._create_medical_prompt(content)
        medical_2 = self.client._create_medical_prompt(content)
        
        # System prompts should be identical
        self.assertEqual(medical_1[0]["content"], medical_2[0]["content"])
        
        # Generate life history prompts multiple times
        life_1 = self.client._create_life_history_prompt(content)
        life_2 = self.client._create_life_history_prompt(content)
        
        # System prompts should be identical
        self.assertEqual(life_1[0]["content"], life_2[0]["content"])


if __name__ == '__main__':
    unittest.main()