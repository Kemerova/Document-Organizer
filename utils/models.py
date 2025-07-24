"""
Data models for Document Organizer.
Defines core data structures for document processing and output.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
from pathlib import Path


@dataclass
class DocumentContent:
    """Represents content extracted from a document file."""
    filename: str
    content: str
    page_numbers: List[int] = field(default_factory=list)
    file_type: str = ""
    ocr_applied: bool = False
    extraction_confidence: float = 1.0
    
    def validate(self) -> bool:
        """Validate document content structure."""
        if not self.filename or not isinstance(self.filename, str):
            return False
        if not isinstance(self.content, str):
            return False
        if not isinstance(self.page_numbers, list):
            return False
        if self.extraction_confidence < 0 or self.extraction_confidence > 1:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'filename': self.filename,
            'content': self.content,
            'page_numbers': self.page_numbers,
            'file_type': self.file_type,
            'ocr_applied': self.ocr_applied,
            'extraction_confidence': self.extraction_confidence
        }


@dataclass
class GPTResponse:
    """Represents a response from GPT processing."""
    chunk_id: str
    structured_data: Dict[str, Any]
    summary: str = ""
    confidence_score: float = 0.0
    source_references: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    
    def validate(self) -> bool:
        """Validate GPT response structure."""
        if not self.chunk_id or not isinstance(self.chunk_id, str):
            return False
        if not isinstance(self.structured_data, dict):
            return False
        if self.confidence_score < 0 or self.confidence_score > 1:
            return False
        if not isinstance(self.source_references, list):
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'chunk_id': self.chunk_id,
            'structured_data': self.structured_data,
            'summary': self.summary,
            'confidence_score': self.confidence_score,
            'source_references': self.source_references,
            'processing_time': self.processing_time
        }


@dataclass
class MedicalRecord:
    """Represents a medical record entry."""
    condition: str
    visit_dates: List[datetime] = field(default_factory=list)
    medications: List[str] = field(default_factory=list)
    physician: str = ""
    notes: str = ""
    source_files: List[str] = field(default_factory=list)
    page_references: List[int] = field(default_factory=list)
    confidence_score: float = 0.0
    
    def validate(self) -> bool:
        """Validate medical record structure."""
        if not self.condition or not isinstance(self.condition, str):
            return False
        if not isinstance(self.visit_dates, list):
            return False
        for date in self.visit_dates:
            if not isinstance(date, datetime):
                return False
        if not isinstance(self.medications, list):
            return False
        if self.confidence_score < 0 or self.confidence_score > 1:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'condition': self.condition,
            'visit_dates': [d.isoformat() for d in self.visit_dates],
            'medications': self.medications,
            'physician': self.physician,
            'notes': self.notes,
            'source_files': self.source_files,
            'page_references': self.page_references,
            'confidence_score': self.confidence_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MedicalRecord':
        """Create MedicalRecord from dictionary."""
        visit_dates = []
        if 'visit_dates' in data:
            for date_str in data['visit_dates']:
                if isinstance(date_str, str):
                    visit_dates.append(datetime.fromisoformat(date_str))
                elif isinstance(date_str, datetime):
                    visit_dates.append(date_str)
        
        return cls(
            condition=data.get('condition', ''),
            visit_dates=visit_dates,
            medications=data.get('medications', []),
            physician=data.get('physician', ''),
            notes=data.get('notes', ''),
            source_files=data.get('source_files', []),
            page_references=data.get('page_references', []),
            confidence_score=data.get('confidence_score', 0.0)
        )


@dataclass
class LifeHistoryRecord:
    """Represents a comprehensive professional career story entry."""
    role: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: str = ""
    department: str = ""
    career_story: str = ""
    key_achievements: List[str] = field(default_factory=list)
    skills_mastered: List[str] = field(default_factory=list)
    leadership_evolution: str = ""
    strategic_impact: str = ""
    career_catalyst: str = ""
    professional_growth: str = ""
    unique_contributions: str = ""
    industry_expertise: str = ""
    source_files: List[str] = field(default_factory=list)
    page_references: List[int] = field(default_factory=list)
    confidence_score: float = 0.0
    
    def validate(self) -> bool:
        """Validate life history record structure."""
        if not self.role or not isinstance(self.role, str):
            return False
        if self.start_date and not isinstance(self.start_date, datetime):
            return False
        if self.end_date and not isinstance(self.end_date, datetime):
            return False
        if self.start_date and self.end_date and self.start_date > self.end_date:
            return False
        if not isinstance(self.key_achievements, list):
            return False
        if not isinstance(self.skills_mastered, list):
            return False
        if self.confidence_score < 0 or self.confidence_score > 1:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'role': self.role,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'location': self.location,
            'department': self.department,
            'career_story': self.career_story,
            'key_achievements': self.key_achievements,
            'skills_mastered': self.skills_mastered,
            'leadership_evolution': self.leadership_evolution,
            'strategic_impact': self.strategic_impact,
            'career_catalyst': self.career_catalyst,
            'professional_growth': self.professional_growth,
            'unique_contributions': self.unique_contributions,
            'industry_expertise': self.industry_expertise,
            'source_files': self.source_files,
            'page_references': self.page_references,
            'confidence_score': self.confidence_score
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LifeHistoryRecord':
        """Create LifeHistoryRecord from dictionary."""
        start_date = None
        if data.get('start_date'):
            start_date = datetime.fromisoformat(data['start_date'])
        
        end_date = None
        if data.get('end_date'):
            end_date = datetime.fromisoformat(data['end_date'])
        
        return cls(
            role=data.get('role', ''),
            start_date=start_date,
            end_date=end_date,
            location=data.get('location', ''),
            department=data.get('department', ''),
            career_story=data.get('career_story', ''),
            key_achievements=data.get('key_achievements', []),
            skills_mastered=data.get('skills_mastered', []),
            leadership_evolution=data.get('leadership_evolution', ''),
            strategic_impact=data.get('strategic_impact', ''),
            career_catalyst=data.get('career_catalyst', ''),
            professional_growth=data.get('professional_growth', ''),
            unique_contributions=data.get('unique_contributions', ''),
            industry_expertise=data.get('industry_expertise', ''),
            source_files=data.get('source_files', []),
            page_references=data.get('page_references', []),
            confidence_score=data.get('confidence_score', 0.0)
        )


@dataclass
class ProcessingMetadata:
    """Tracks processing state and statistics."""
    total_files: int = 0
    processed_files: int = 0
    failed_files: List[str] = field(default_factory=list)
    total_tokens: int = 0
    api_calls_made: int = 0
    processing_time: float = 0.0
    output_files_generated: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def validate(self) -> bool:
        """Validate processing metadata structure."""
        if self.total_files < 0 or self.processed_files < 0:
            return False
        if self.processed_files > self.total_files:
            return False
        if not isinstance(self.failed_files, list):
            return False
        if self.total_tokens < 0 or self.api_calls_made < 0:
            return False
        if self.processing_time < 0:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'total_files': self.total_files,
            'processed_files': self.processed_files,
            'failed_files': self.failed_files,
            'total_tokens': self.total_tokens,
            'api_calls_made': self.api_calls_made,
            'processing_time': self.processing_time,
            'output_files_generated': self.output_files_generated,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }
    
    def get_success_rate(self) -> float:
        """Calculate processing success rate."""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files - len(self.failed_files)) / self.total_files
    
    def get_processing_speed(self) -> float:
        """Calculate files processed per second."""
        if self.processing_time == 0:
            return 0.0
        return self.processed_files / self.processing_time
    
    def add_failed_file(self, filename: str) -> None:
        """Add a file to the failed files list."""
        if filename not in self.failed_files:
            self.failed_files.append(filename)
    
    def increment_processed(self) -> None:
        """Increment processed file count."""
        self.processed_files += 1
    
    def add_output_file(self, filepath: str) -> None:
        """Add an output file to the generated files list."""
        if filepath not in self.output_files_generated:
            self.output_files_generated.append(filepath)


@dataclass
class ChunkMetadata:
    """Metadata for content chunks."""
    chunk_id: str
    source_file: str
    page_numbers: List[int] = field(default_factory=list)
    token_count: int = 0
    chunk_index: int = 0
    total_chunks: int = 0
    
    def validate(self) -> bool:
        """Validate chunk metadata structure."""
        if not self.chunk_id or not isinstance(self.chunk_id, str):
            return False
        if not self.source_file or not isinstance(self.source_file, str):
            return False
        if self.token_count < 0:
            return False
        if self.chunk_index < 0 or self.total_chunks < 0:
            return False
        if self.chunk_index >= self.total_chunks and self.total_chunks > 0:
            return False
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'chunk_id': self.chunk_id,
            'source_file': self.source_file,
            'page_numbers': self.page_numbers,
            'token_count': self.token_count,
            'chunk_index': self.chunk_index,
            'total_chunks': self.total_chunks
        }


def save_json_backup(data: Any, filepath: str) -> None:
    """Save data as JSON backup with proper formatting."""
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    def json_serializer(obj):
        """Custom JSON serializer for datetime and other objects."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif isinstance(obj, Path):
            return str(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=json_serializer)


def load_json_backup(filepath: str) -> Any:
    """Load data from JSON backup file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)