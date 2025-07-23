"""
Azure OpenAI GPT client with async processing capabilities.
Handles parallel GPT API calls with retry logic and rate limiting.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional, Tuple
import aiohttp
from aiohttp import ClientTimeout
import backoff

from .config import Config
from .chunker import ContentChunk

logger = logging.getLogger(__name__)


@dataclass
class GPTResponse:
    """Represents a response from GPT processing."""
    chunk_id: str
    structured_data: Dict[str, Any]
    summary: str
    confidence_score: float
    source_references: List[str]
    processing_time: float
    token_usage: Dict[str, int]
    raw_response: str


class GPTError(Exception):
    """Raised when GPT processing fails."""
    pass


class AzureGPTClient:
    """Async Azure OpenAI GPT client with parallel processing."""
    
    def __init__(self, config: Config):
        """
        Initialize the Azure GPT client.
        
        Args:
            config: Configuration object with Azure OpenAI settings
        """
        self.config = config
        self.endpoint = config.azure_openai.endpoint
        self.api_key = config.azure_openai.api_key
        self.deployment_name = config.azure_openai.deployment_name
        self.api_version = config.azure_openai.api_version
        
        self.max_concurrent = config.processing.max_concurrent_requests
        self.retry_attempts = config.processing.retry_attempts
        
        # Rate limiting
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self.last_request_time = 0
        self.min_request_interval = 0.1  # Minimum time between requests
        
        # Statistics
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_tokens_used = 0
        
        logger.info(f"Initialized Azure GPT client with {self.max_concurrent} max concurrent requests")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Azure OpenAI API requests."""
        return {
            'api-key': self.api_key,
            'Content-Type': 'application/json'
        }
    
    def _get_api_url(self) -> str:
        """Get the Azure OpenAI API URL."""
        return (f"{self.endpoint}openai/deployments/{self.deployment_name}/"
                f"chat/completions?api-version={self.api_version}")
    
    def _create_medical_prompt(self, content: str) -> List[Dict[str, str]]:
        """Create prompt for medical document processing."""
        system_prompt = """You are a medical document analyzer. Extract structured information from medical documents and return it as JSON.

For each medical condition, medication, or significant finding, extract:
- condition: The medical condition or diagnosis
- visit_dates: List of dates when this was mentioned (format: YYYY-MM-DD, use "unknown" if not clear)
- medications: List of medications related to this condition
- physician: Name of physician or medical facility
- notes: Important notes or details
- confidence: Your confidence in this extraction (0.0 to 1.0)

Return ONLY valid JSON in this format:
{
  "medical_records": [
    {
      "condition": "condition name",
      "visit_dates": ["2023-01-15", "2023-02-20"],
      "medications": ["medication1", "medication2"],
      "physician": "Dr. Smith",
      "notes": "relevant notes",
      "confidence": 0.9
    }
  ],
  "summary": "Brief summary of the medical content"
}"""
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this medical document content:\n\n{content}"}
        ]
    
    def _create_life_history_prompt(self, content: str) -> List[Dict[str, str]]:
        """Create prompt for life history document processing."""
        system_prompt = """You are a career and life history analyzer. Extract structured information from career documents and return it as JSON.

For each role, position, achievement, or significant life event, extract:
- role: Job title, position, or type of achievement
- start_date: Start date (format: YYYY-MM-DD, use "unknown" if not clear)
- end_date: End date (format: YYYY-MM-DD, use "ongoing" if current, "unknown" if not clear)
- location: Location, organization, or institution
- key_achievements: List of notable achievements or responsibilities
- confidence: Your confidence in this extraction (0.0 to 1.0)

Return ONLY valid JSON in this format:
{
  "life_history_records": [
    {
      "role": "Software Engineer",
      "start_date": "2020-01-15",
      "end_date": "2022-12-31",
      "location": "Tech Company Inc.",
      "key_achievements": ["Led team of 5", "Increased efficiency by 30%"],
      "confidence": 0.9
    }
  ],
  "summary": "Brief summary of the career/life content"
}"""
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this career/life document content:\n\n{content}"}
        ]
    
    def _create_outline_prompt(self, summaries: List[str]) -> List[Dict[str, str]]:
        """Create prompt for generating document collection outline."""
        system_prompt = """You are a document organizer. Create a comprehensive outline from document summaries.

Create a structured outline that:
1. Groups related content logically
2. Maintains chronological order where relevant
3. Highlights key themes and patterns
4. Provides a clear overview of the entire collection

Return ONLY valid JSON in this format:
{
  "outline": {
    "title": "Document Collection Overview",
    "sections": [
      {
        "section_title": "Section Name",
        "subsections": [
          {
            "title": "Subsection Name",
            "content": "Description of content",
            "document_count": 5
          }
        ]
      }
    ]
  },
  "key_themes": ["theme1", "theme2"],
  "date_range": "2020-2023",
  "total_documents": 50
}"""
        
        combined_summaries = "\n\n".join([f"Summary {i+1}: {summary}" 
                                        for i, summary in enumerate(summaries)])
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Create an outline from these document summaries:\n\n{combined_summaries}"}
        ]
    
    @backoff.on_exception(
        backoff.expo,
        (aiohttp.ClientError, asyncio.TimeoutError),
        max_tries=3,
        max_time=60
    )
    async def _make_api_request(self, session: aiohttp.ClientSession, 
                               messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Make a single API request with retry logic.
        
        Args:
            session: aiohttp session
            messages: Messages to send to GPT
            
        Returns:
            API response dictionary
        """
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        self.last_request_time = time.time()
        
        payload = {
            "messages": messages,
            "max_tokens": 4000,
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        timeout = ClientTimeout(total=120)  # 2 minute timeout
        
        async with session.post(
            self._get_api_url(),
            headers=self._get_headers(),
            json=payload,
            timeout=timeout
        ) as response:
            self.total_requests += 1
            
            if response.status == 429:  # Rate limited
                retry_after = int(response.headers.get('Retry-After', 60))
                logger.warning(f"Rate limited, waiting {retry_after} seconds")
                await asyncio.sleep(retry_after)
                raise aiohttp.ClientError("Rate limited")
            
            if response.status != 200:
                error_text = await response.text()
                raise GPTError(f"API request failed with status {response.status}: {error_text}")
            
            result = await response.json()
            self.successful_requests += 1
            
            # Track token usage
            if 'usage' in result:
                self.total_tokens_used += result['usage'].get('total_tokens', 0)
            
            return result
    
    async def process_chunk_async(self, chunk: ContentChunk, mode: str) -> GPTResponse:
        """
        Process a single chunk asynchronously.
        
        Args:
            chunk: Content chunk to process
            mode: Processing mode ('medical' or 'life')
            
        Returns:
            GPTResponse object
        """
        async with self.semaphore:  # Limit concurrency
            start_time = time.time()
            
            try:
                # Create appropriate prompt based on mode
                if mode == 'medical':
                    messages = self._create_medical_prompt(chunk.content)
                elif mode == 'life':
                    messages = self._create_life_history_prompt(chunk.content)
                else:
                    raise GPTError(f"Unknown processing mode: {mode}")
                
                # Make API request
                timeout = ClientTimeout(total=120)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    response = await self._make_api_request(session, messages)
                
                # Parse response
                content = response['choices'][0]['message']['content']
                
                try:
                    structured_data = json.loads(content)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response for chunk {chunk.chunk_id}: {e}")
                    structured_data = {"error": "Failed to parse JSON", "raw_content": content}
                
                # Extract summary
                summary = structured_data.get('summary', 'No summary available')
                
                # Calculate confidence score
                if mode == 'medical':
                    records = structured_data.get('medical_records', [])
                elif mode == 'life':
                    records = structured_data.get('life_history_records', [])
                else:
                    records = []
                
                confidences = [record.get('confidence', 0.5) for record in records]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
                
                processing_time = time.time() - start_time
                
                # Get token usage
                token_usage = response.get('usage', {})
                
                logger.info(f"Processed chunk {chunk.chunk_id} in {processing_time:.2f}s "
                           f"with {len(records)} records extracted")
                
                return GPTResponse(
                    chunk_id=chunk.chunk_id,
                    structured_data=structured_data,
                    summary=summary,
                    confidence_score=avg_confidence,
                    source_references=chunk.source_files,
                    processing_time=processing_time,
                    token_usage=token_usage,
                    raw_response=content
                )
                
            except Exception as e:
                self.failed_requests += 1
                processing_time = time.time() - start_time
                
                logger.error(f"Failed to process chunk {chunk.chunk_id}: {e}")
                
                # Return error response
                return GPTResponse(
                    chunk_id=chunk.chunk_id,
                    structured_data={"error": str(e)},
                    summary=f"Processing failed: {e}",
                    confidence_score=0.0,
                    source_references=chunk.source_files,
                    processing_time=processing_time,
                    token_usage={},
                    raw_response=""
                )
    
    async def batch_process_chunks(self, chunks: List[ContentChunk], 
                                 mode: str, progress_callback=None) -> List[GPTResponse]:
        """
        Process multiple chunks in parallel.
        
        Args:
            chunks: List of chunks to process
            mode: Processing mode ('medical' or 'life')
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of GPTResponse objects
        """
        logger.info(f"Starting batch processing of {len(chunks)} chunks in {mode} mode")
        
        # Create tasks for all chunks
        tasks = [self.process_chunk_async(chunk, mode) for chunk in chunks]
        
        # Process with progress tracking
        responses = []
        completed = 0
        
        for task in asyncio.as_completed(tasks):
            response = await task
            responses.append(response)
            completed += 1
            
            if progress_callback:
                progress_callback(completed, len(chunks))
        
        # Sort responses by chunk_id to maintain order
        responses.sort(key=lambda r: r.chunk_id)
        
        logger.info(f"Completed batch processing: {self.successful_requests} successful, "
                   f"{self.failed_requests} failed, {self.total_tokens_used} tokens used")
        
        return responses
    
    async def generate_outline(self, summaries: List[str]) -> Dict[str, Any]:
        """
        Generate an outline from document summaries.
        
        Args:
            summaries: List of document summaries
            
        Returns:
            Outline dictionary
        """
        if not summaries:
            return {"outline": {"title": "Empty Collection", "sections": []}}
        
        try:
            messages = self._create_outline_prompt(summaries)
            
            timeout = ClientTimeout(total=120)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                response = await self._make_api_request(session, messages)
            
            content = response['choices'][0]['message']['content']
            outline_data = json.loads(content)
            
            logger.info("Generated document collection outline")
            return outline_data
            
        except Exception as e:
            logger.error(f"Failed to generate outline: {e}")
            return {
                "outline": {
                    "title": "Document Collection Overview",
                    "sections": [{"section_title": "Processing Error", 
                                "subsections": [{"title": "Error", "content": str(e), "document_count": 0}]}]
                },
                "error": str(e)
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": success_rate,
            "total_tokens_used": self.total_tokens_used,
            "max_concurrent_requests": self.max_concurrent
        }