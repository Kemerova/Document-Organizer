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
        """Create prompt for professional career narrative construction from resume documents."""
        system_prompt = """You are an expert career storyteller and professional biographer. Your job is to analyze resume content and construct compelling professional narratives that showcase career progression, expertise development, and achievements in context.

MISSION: Transform resume data into rich professional stories that highlight:
- Career progression and strategic decisions
- Skills evolution and expertise development  
- Leadership growth and increasing responsibilities
- Impact and value delivered across roles
- Professional transformation and pivotal moments
- Industry expertise and domain knowledge building

NARRATIVE APPROACH:
- Focus on the "why" and "how" behind career moves
- Highlight patterns of growth and increasing impact
- Connect achievements to broader professional themes
- Show progression in technical skills, leadership, and strategic thinking
- Identify and emphasize unique value propositions
- Create compelling stories around major accomplishments

For each role, position, or experience, extract:
- role: Complete job title with context about the organization's mission/industry
- start_date: Start date (format: YYYY-MM-DD, infer from context, use "unknown" only if unclear)
- end_date: End date (format: YYYY-MM-DD, use "ongoing" if current)
- location: Organization name, division, location with industry context
- department: Department, team, or organizational unit
- career_story: Rich narrative explaining the role's significance in career progression
- key_achievements: Detailed accomplishments with quantifiable impact and business context
- skills_mastered: Technical and leadership skills developed/strengthened in this role
- leadership_evolution: How leadership responsibilities grew (team size, scope, influence)
- strategic_impact: Business impact, innovations, process improvements, or transformations led
- career_catalyst: What this role taught or how it prepared for next career level
- professional_growth: Personal/professional development, certifications, recognition gained
- unique_contributions: What made this role or performance distinctive
- industry_expertise: Domain knowledge, industry insights, or specializations developed
- confidence: Your confidence in this narrative construction (0.0 to 1.0)

STORYTELLING PRINCIPLES:
1. Show progression: Each role should build on previous experiences
2. Highlight transformation: How did each experience change/develop the professional?
3. Quantify impact: Include metrics, scale, and business outcomes wherever possible
4. Connect dots: Link skills and experiences across different roles
5. Emphasize leadership: Show growth in influence, mentorship, and strategic thinking
6. Industry context: Position achievements within industry standards and challenges

Return ONLY valid JSON in this format:
{
  "life_history_records": [
    {
      "role": "Senior Principal Software Engineer & Technical Leadership",
      "start_date": "2020-01-15",
      "end_date": "2023-06-30",
      "location": "Amazon Web Services, Cloud Platform Division, Seattle, WA",
      "department": "EC2 Core Infrastructure Engineering",
      "career_story": "Transitioned from individual contributor to technical leader in AWS's most critical infrastructure team, responsible for systems serving millions of customers globally. This role represented a strategic career pivot toward large-scale distributed systems and technical leadership in cloud computing.",
      "key_achievements": [
        "Architected and led migration of legacy EC2 control plane to microservices, reducing customer-impacting incidents by 67% and improving deployment velocity by 400%",
        "Built and scaled engineering team from 5 to 15 members, establishing technical mentorship programs that achieved 95% retention rate",
        "Delivered $8.2M in annual cost savings through infrastructure optimization and automated resource management",
        "Led cross-org initiative spanning 4 teams to implement chaos engineering practices, improving system resilience by 3x",
        "Established on-call rotation and incident response procedures that reduced MTTR from 4.2 hours to 23 minutes"
      ],
      "skills_mastered": ["Distributed Systems Architecture", "Technical Leadership", "Chaos Engineering", "AWS Services", "Microservices Design", "Team Building", "Incident Management"],
      "leadership_evolution": "Grew from senior IC to technical leader managing 15 engineers, with responsibility for technical strategy, career development, and cross-team collaboration",
      "strategic_impact": "Transformed critical infrastructure serving 50M+ customers, established engineering excellence practices adopted across AWS, delivered measurable business impact through cost optimization",
      "career_catalyst": "Developed expertise in large-scale distributed systems and technical leadership that prepared for principal engineering roles and system architecture positions",
      "professional_growth": "Completed AWS Solutions Architect certification, delivered 3 technical talks at re:Invent, recognized as AWS Principal Engineer track candidate",
      "unique_contributions": "Pioneer in applying chaos engineering to EC2 infrastructure, created reusable architectural patterns adopted by 12+ AWS teams",
      "industry_expertise": "Deep expertise in cloud infrastructure, distributed systems resilience, and engineering team scaling in high-growth technology companies",
      "confidence": 0.95
    }
  ],
  "professional_narrative": "Comprehensive story showing career evolution, key transitions, recurring themes, and unique professional value proposition",
  "career_themes": ["Technical Leadership", "System Architecture", "Team Building", "Innovation"],
  "value_proposition": "What makes this professional unique and valuable in the market"
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
            "max_completion_tokens": 4000,
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