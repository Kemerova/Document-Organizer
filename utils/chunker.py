"""
Token-aware content chunking system for Document Organizer.
Handles intelligent content segmentation while preserving document boundaries.
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import re

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class ContentChunk:
    """Represents a chunk of content with metadata."""
    chunk_id: str
    content: str
    token_count: int
    source_files: List[str]
    page_references: List[int]
    chunk_index: int
    total_chunks: int
    document_boundaries: List[str]  # Documents that start/end in this chunk


class ChunkingError(Exception):
    """Raised when content chunking fails."""
    pass


class TokenAwareChunker:
    """Handles intelligent content chunking with token awareness."""
    
    def __init__(self, model_name: str = "gpt-4-1106-preview", max_tokens: int = 8000):
        """
        Initialize the chunker.
        
        Args:
            model_name: Name of the model for token counting
            max_tokens: Maximum tokens per chunk
        """
        if not TIKTOKEN_AVAILABLE:
            raise ChunkingError(
                "tiktoken not available. Please install: pip install tiktoken"
            )
        
        try:
            self.encoding = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base encoding for GPT-4
            self.encoding = tiktoken.get_encoding("cl100k_base")
            logger.warning(f"Model {model_name} not found, using cl100k_base encoding")
        
        self.max_tokens = max_tokens
        self.model_name = model_name
        
        # Reserve tokens for system prompt and response
        self.reserved_tokens = 1000
        self.effective_max_tokens = max_tokens - self.reserved_tokens
        
        logger.info(f"Initialized chunker for {model_name} with {self.effective_max_tokens} effective tokens per chunk")
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Number of tokens
        """
        try:
            return len(self.encoding.encode(text))
        except Exception as e:
            logger.warning(f"Error counting tokens: {e}")
            # Fallback: rough estimation (4 chars per token)
            return len(text) // 4
    
    def split_by_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences for better chunking boundaries.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting - can be enhanced with more sophisticated NLP
        sentence_endings = r'[.!?]+\s+'
        sentences = re.split(sentence_endings, text)
        
        # Clean up and filter empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def find_optimal_split_point(self, text: str, max_tokens: int) -> int:
        """
        Find the optimal point to split text while respecting token limits.
        
        Args:
            text: Text to split
            max_tokens: Maximum tokens allowed
            
        Returns:
            Character position to split at
        """
        if self.count_tokens(text) <= max_tokens:
            return len(text)
        
        # Try to split at paragraph boundaries first
        paragraphs = text.split('\n\n')
        current_text = ""
        
        for paragraph in paragraphs:
            test_text = current_text + ('\n\n' if current_text else '') + paragraph
            if self.count_tokens(test_text) > max_tokens:
                if current_text:
                    return len(current_text)
                else:
                    # Single paragraph is too long, split by sentences
                    return self._split_paragraph_by_sentences(paragraph, max_tokens)
            current_text = test_text
        
        return len(text)
    
    def _split_paragraph_by_sentences(self, paragraph: str, max_tokens: int) -> int:
        """Split a paragraph by sentences when it's too long."""
        sentences = self.split_by_sentences(paragraph)
        current_text = ""
        
        for sentence in sentences:
            test_text = current_text + (' ' if current_text else '') + sentence
            if self.count_tokens(test_text) > max_tokens:
                if current_text:
                    return len(current_text)
                else:
                    # Single sentence is too long, split by words
                    return self._split_sentence_by_words(sentence, max_tokens)
            current_text = test_text
        
        return len(paragraph)
    
    def _split_sentence_by_words(self, sentence: str, max_tokens: int) -> int:
        """Split a sentence by words when it's too long."""
        words = sentence.split()
        current_text = ""
        
        for word in words:
            test_text = current_text + (' ' if current_text else '') + word
            if self.count_tokens(test_text) > max_tokens:
                return len(current_text) if current_text else len(word)
            current_text = test_text
        
        return len(sentence)
    
    def chunk_content(self, documents: List[Dict[str, Any]]) -> List[ContentChunk]:
        """
        Chunk a list of documents into token-aware chunks.
        
        Args:
            documents: List of document dictionaries with keys:
                      - filename: str
                      - content: str
                      - page_numbers: List[int]
                      - file_type: str
                      
        Returns:
            List of ContentChunk objects
        """
        chunks = []
        chunk_index = 0
        
        # First pass: estimate total chunks needed
        total_tokens = sum(self.count_tokens(doc['content']) for doc in documents)
        estimated_chunks = max(1, (total_tokens + self.effective_max_tokens - 1) // self.effective_max_tokens)
        
        logger.info(f"Chunking {len(documents)} documents with ~{total_tokens} total tokens "
                   f"into ~{estimated_chunks} chunks")
        
        current_chunk_content = ""
        current_chunk_files = []
        current_chunk_pages = []
        current_boundaries = []
        
        for doc in documents:
            filename = doc['filename']
            content = doc['content']
            page_numbers = doc.get('page_numbers', [1])
            
            if not content.strip():
                logger.warning(f"Skipping empty document: {filename}")
                continue
            
            # Add document boundary marker
            doc_header = f"\n\n=== Document: {filename} ===\n"
            remaining_content = doc_header + content
            
            while remaining_content:
                # Calculate available space in current chunk
                current_tokens = self.count_tokens(current_chunk_content)
                available_tokens = self.effective_max_tokens - current_tokens
                
                if available_tokens <= 100:  # Not enough space, finalize current chunk
                    if current_chunk_content.strip():
                        chunks.append(self._create_chunk(
                            chunk_index, current_chunk_content, current_chunk_files,
                            current_chunk_pages, current_boundaries, estimated_chunks
                        ))
                        chunk_index += 1
                    
                    # Reset for new chunk
                    current_chunk_content = ""
                    current_chunk_files = []
                    current_chunk_pages = []
                    current_boundaries = []
                    available_tokens = self.effective_max_tokens
                
                # Find optimal split point
                split_point = self.find_optimal_split_point(remaining_content, available_tokens)
                
                if split_point == 0:
                    # Content is too large even for empty chunk, force split
                    split_point = len(remaining_content) // 2
                    logger.warning(f"Force splitting content from {filename}")
                
                # Add content to current chunk
                chunk_part = remaining_content[:split_point]
                current_chunk_content += chunk_part
                
                # Track metadata
                if filename not in current_chunk_files:
                    current_chunk_files.append(filename)
                    current_chunk_pages.extend(page_numbers)
                    current_boundaries.append(f"Start: {filename}")
                
                # Update remaining content
                remaining_content = remaining_content[split_point:].strip()
                
                if not remaining_content:
                    current_boundaries.append(f"End: {filename}")
        
        # Finalize last chunk
        if current_chunk_content.strip():
            chunks.append(self._create_chunk(
                chunk_index, current_chunk_content, current_chunk_files,
                current_chunk_pages, current_boundaries, len(chunks) + 1
            ))
        
        logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")
        return chunks
    
    def _create_chunk(self, index: int, content: str, files: List[str], 
                     pages: List[int], boundaries: List[str], total: int) -> ContentChunk:
        """Create a ContentChunk object."""
        chunk_id = f"chunk_{index:04d}"
        token_count = self.count_tokens(content)
        
        return ContentChunk(
            chunk_id=chunk_id,
            content=content.strip(),
            token_count=token_count,
            source_files=files.copy(),
            page_references=sorted(list(set(pages))),
            chunk_index=index,
            total_chunks=total,
            document_boundaries=boundaries.copy()
        )
    
    def get_chunk_summary(self, chunks: List[ContentChunk]) -> Dict[str, Any]:
        """
        Get summary statistics about chunks.
        
        Args:
            chunks: List of chunks to analyze
            
        Returns:
            Dictionary with chunk statistics
        """
        if not chunks:
            return {"total_chunks": 0, "total_tokens": 0}
        
        total_tokens = sum(chunk.token_count for chunk in chunks)
        avg_tokens = total_tokens / len(chunks)
        max_tokens = max(chunk.token_count for chunk in chunks)
        min_tokens = min(chunk.token_count for chunk in chunks)
        
        all_files = set()
        for chunk in chunks:
            all_files.update(chunk.source_files)
        
        return {
            "total_chunks": len(chunks),
            "total_tokens": total_tokens,
            "average_tokens_per_chunk": avg_tokens,
            "max_tokens_per_chunk": max_tokens,
            "min_tokens_per_chunk": min_tokens,
            "unique_source_files": len(all_files),
            "token_efficiency": (avg_tokens / self.effective_max_tokens) * 100
        }
    
    def validate_chunks(self, chunks: List[ContentChunk]) -> List[str]:
        """
        Validate chunks for potential issues.
        
        Args:
            chunks: List of chunks to validate
            
        Returns:
            List of validation warnings
        """
        warnings = []
        
        for chunk in chunks:
            if chunk.token_count > self.effective_max_tokens:
                warnings.append(f"Chunk {chunk.chunk_id} exceeds token limit: "
                               f"{chunk.token_count} > {self.effective_max_tokens}")
            
            if chunk.token_count < 100:
                warnings.append(f"Chunk {chunk.chunk_id} is very small: "
                               f"{chunk.token_count} tokens")
            
            if not chunk.source_files:
                warnings.append(f"Chunk {chunk.chunk_id} has no source files")
        
        return warnings


def is_tiktoken_available() -> bool:
    """Check if tiktoken is available."""
    return TIKTOKEN_AVAILABLE