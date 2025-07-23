"""
Data consolidation and deduplication engine for Document Organizer.
Handles merging and deduplication of GPT responses with source tracking.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Set, Optional, Tuple
import re
from difflib import SequenceMatcher

from .azure_gpt import GPTResponse
from .models import MedicalRecord, LifeHistoryRecord

logger = logging.getLogger(__name__)


@dataclass
class ConsolidatedData:
    """Container for consolidated and deduplicated data."""
    medical_records: List[MedicalRecord] = field(default_factory=list)
    life_history_records: List[LifeHistoryRecord] = field(default_factory=list)
    summaries: List[str] = field(default_factory=list)
    source_files: Set[str] = field(default_factory=set)
    processing_metadata: Dict[str, Any] = field(default_factory=dict)
    deduplication_log: List[str] = field(default_factory=list)


class DataProcessor:
    """Handles data consolidation and deduplication."""
    
    def __init__(self, similarity_threshold: float = 0.8):
        """
        Initialize the data processor.
        
        Args:
            similarity_threshold: Threshold for considering items similar (0.0 to 1.0)
        """
        self.similarity_threshold = similarity_threshold
        self.deduplication_log = []
        
        logger.info(f"Initialized data processor with similarity threshold {similarity_threshold}")
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate similarity between two text strings.
        
        Args:
            text1: First text string
            text2: Second text string
            
        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not text1 or not text2:
            return 0.0
        
        # Normalize text for comparison
        norm1 = self._normalize_text(text1)
        norm2 = self._normalize_text(text2)
        
        return SequenceMatcher(None, norm1, norm2).ratio()
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Convert to lowercase and remove extra whitespace
        text = re.sub(r'\s+', ' ', text.lower().strip())
        # Remove common punctuation
        text = re.sub(r'[.,;:!?()"\'-]', '', text)
        return text
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string into datetime object.
        
        Args:
            date_str: Date string to parse
            
        Returns:
            datetime object or None if parsing fails
        """
        if not date_str or date_str.lower() in ['unknown', 'ongoing', 'current']:
            return None
        
        # Common date formats
        date_formats = [
            '%Y-%m-%d',
            '%Y-%m',
            '%Y',
            '%m/%d/%Y',
            '%m-%d-%Y',
            '%d/%m/%Y',
            '%d-%m-%Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def consolidate_responses(self, responses: List[GPTResponse], mode: str) -> ConsolidatedData:
        """
        Consolidate GPT responses into structured data.
        
        Args:
            responses: List of GPT responses to consolidate
            mode: Processing mode ('medical' or 'life')
            
        Returns:
            ConsolidatedData object
        """
        logger.info(f"Consolidating {len(responses)} responses in {mode} mode")
        
        consolidated = ConsolidatedData()
        
        # Track processing metadata
        consolidated.processing_metadata = {
            "total_responses": len(responses),
            "successful_responses": len([r for r in responses if 'error' not in r.structured_data]),
            "failed_responses": len([r for r in responses if 'error' in r.structured_data]),
            "mode": mode,
            "processing_timestamp": datetime.now().isoformat()
        }
        
        # Collect all summaries and source files
        for response in responses:
            if response.summary and response.summary != "No summary available":
                consolidated.summaries.append(response.summary)
            consolidated.source_files.update(response.source_references)
        
        # Process based on mode
        if mode == 'medical':
            consolidated.medical_records = self._consolidate_medical_data(responses)
        elif mode == 'life':
            consolidated.life_history_records = self._consolidate_life_data(responses)
        else:
            logger.error(f"Unknown consolidation mode: {mode}")
        
        consolidated.deduplication_log = self.deduplication_log.copy()
        
        logger.info(f"Consolidation complete: {len(consolidated.medical_records)} medical records, "
                   f"{len(consolidated.life_history_records)} life records")
        
        return consolidated
    
    def _consolidate_medical_data(self, responses: List[GPTResponse]) -> List[MedicalRecord]:
        """Consolidate medical data with deduplication."""
        all_records = []
        
        # Extract all medical records from responses
        for response in responses:
            if 'error' in response.structured_data:
                continue
            
            records = response.structured_data.get('medical_records', [])
            for record_data in records:
                try:
                    # Parse visit dates
                    visit_dates = []
                    for date_str in record_data.get('visit_dates', []):
                        parsed_date = self._parse_date(date_str)
                        if parsed_date:
                            visit_dates.append(parsed_date)
                    
                    record = MedicalRecord(
                        condition=record_data.get('condition', '').strip(),
                        visit_dates=visit_dates,
                        medications=record_data.get('medications', []),
                        physician=record_data.get('physician', '').strip(),
                        notes=record_data.get('notes', '').strip(),
                        source_files=response.source_references.copy(),
                        page_references=[],  # Will be populated from chunk metadata
                        confidence_score=record_data.get('confidence', 0.5)
                    )
                    
                    if record.condition:  # Only add records with conditions
                        all_records.append(record)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse medical record: {e}")
                    continue
        
        # Deduplicate medical records
        return self._deduplicate_medical_records(all_records)
    
    def _deduplicate_medical_records(self, records: List[MedicalRecord]) -> List[MedicalRecord]:
        """Deduplicate medical records by merging similar conditions."""
        if not records:
            return []
        
        deduplicated = []
        processed_indices = set()
        
        for i, record in enumerate(records):
            if i in processed_indices:
                continue
            
            # Find similar records
            similar_records = [record]
            processed_indices.add(i)
            
            for j, other_record in enumerate(records[i+1:], i+1):
                if j in processed_indices:
                    continue
                
                # Check if conditions are similar
                condition_similarity = self.calculate_similarity(record.condition, other_record.condition)
                physician_similarity = self.calculate_similarity(record.physician, other_record.physician)
                
                if (condition_similarity >= self.similarity_threshold or 
                    (condition_similarity >= 0.6 and physician_similarity >= 0.7)):
                    similar_records.append(other_record)
                    processed_indices.add(j)
            
            # Merge similar records
            if len(similar_records) > 1:
                merged_record = self._merge_medical_records(similar_records)
                deduplicated.append(merged_record)
                
                self.deduplication_log.append(
                    f"Merged {len(similar_records)} medical records for condition: {merged_record.condition}"
                )
            else:
                deduplicated.append(record)
        
        logger.info(f"Deduplicated {len(records)} medical records to {len(deduplicated)}")
        return deduplicated
    
    def _merge_medical_records(self, records: List[MedicalRecord]) -> MedicalRecord:
        """Merge multiple medical records into one."""
        if not records:
            raise ValueError("Cannot merge empty list of records")
        
        if len(records) == 1:
            return records[0]
        
        # Use the record with highest confidence as base
        base_record = max(records, key=lambda r: r.confidence_score)
        
        # Merge all data
        all_visit_dates = set()
        all_medications = set()
        all_source_files = set()
        all_page_refs = set()
        all_notes = []
        
        for record in records:
            all_visit_dates.update(record.visit_dates)
            all_medications.update(record.medications)
            all_source_files.update(record.source_files)
            all_page_refs.update(record.page_references)
            if record.notes and record.notes not in all_notes:
                all_notes.append(record.notes)
        
        # Calculate average confidence
        avg_confidence = sum(r.confidence_score for r in records) / len(records)
        
        return MedicalRecord(
            condition=base_record.condition,
            visit_dates=sorted(list(all_visit_dates)),
            medications=sorted(list(all_medications)),
            physician=base_record.physician,
            notes=' | '.join(all_notes),
            source_files=sorted(list(all_source_files)),
            page_references=sorted(list(all_page_refs)),
            confidence_score=avg_confidence
        )
    
    def _consolidate_life_data(self, responses: List[GPTResponse]) -> List[LifeHistoryRecord]:
        """Consolidate life history data with deduplication."""
        all_records = []
        
        # Extract all life history records from responses
        for response in responses:
            if 'error' in response.structured_data:
                continue
            
            records = response.structured_data.get('life_history_records', [])
            for record_data in records:
                try:
                    # Parse dates
                    start_date = self._parse_date(record_data.get('start_date', ''))
                    end_date = self._parse_date(record_data.get('end_date', ''))
                    
                    record = LifeHistoryRecord(
                        role=record_data.get('role', '').strip(),
                        start_date=start_date,
                        end_date=end_date,
                        location=record_data.get('location', '').strip(),
                        key_achievements=record_data.get('key_achievements', []),
                        source_files=response.source_references.copy(),
                        page_references=[],  # Will be populated from chunk metadata
                        confidence_score=record_data.get('confidence', 0.5)
                    )
                    
                    if record.role:  # Only add records with roles
                        all_records.append(record)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse life history record: {e}")
                    continue
        
        # Deduplicate life history records
        return self._deduplicate_life_records(all_records)
    
    def _deduplicate_life_records(self, records: List[LifeHistoryRecord]) -> List[LifeHistoryRecord]:
        """Deduplicate life history records by merging similar roles."""
        if not records:
            return []
        
        deduplicated = []
        processed_indices = set()
        
        for i, record in enumerate(records):
            if i in processed_indices:
                continue
            
            # Find similar records
            similar_records = [record]
            processed_indices.add(i)
            
            for j, other_record in enumerate(records[i+1:], i+1):
                if j in processed_indices:
                    continue
                
                # Check if roles and locations are similar
                role_similarity = self.calculate_similarity(record.role, other_record.role)
                location_similarity = self.calculate_similarity(record.location, other_record.location)
                
                if (role_similarity >= self.similarity_threshold and 
                    location_similarity >= 0.6):
                    similar_records.append(other_record)
                    processed_indices.add(j)
            
            # Merge similar records
            if len(similar_records) > 1:
                merged_record = self._merge_life_records(similar_records)
                deduplicated.append(merged_record)
                
                self.deduplication_log.append(
                    f"Merged {len(similar_records)} life history records for role: {merged_record.role}"
                )
            else:
                deduplicated.append(record)
        
        logger.info(f"Deduplicated {len(records)} life history records to {len(deduplicated)}")
        return deduplicated
    
    def _merge_life_records(self, records: List[LifeHistoryRecord]) -> LifeHistoryRecord:
        """Merge multiple life history records into one."""
        if not records:
            raise ValueError("Cannot merge empty list of records")
        
        if len(records) == 1:
            return records[0]
        
        # Use the record with highest confidence as base
        base_record = max(records, key=lambda r: r.confidence_score)
        
        # Find the earliest start date and latest end date
        start_dates = [r.start_date for r in records if r.start_date]
        end_dates = [r.end_date for r in records if r.end_date]
        
        earliest_start = min(start_dates) if start_dates else None
        latest_end = max(end_dates) if end_dates else None
        
        # Merge all data
        all_achievements = set()
        all_source_files = set()
        all_page_refs = set()
        
        for record in records:
            all_achievements.update(record.key_achievements)
            all_source_files.update(record.source_files)
            all_page_refs.update(record.page_references)
        
        # Calculate average confidence
        avg_confidence = sum(r.confidence_score for r in records) / len(records)
        
        return LifeHistoryRecord(
            role=base_record.role,
            start_date=earliest_start,
            end_date=latest_end,
            location=base_record.location,
            key_achievements=sorted(list(all_achievements)),
            source_files=sorted(list(all_source_files)),
            page_references=sorted(list(all_page_refs)),
            confidence_score=avg_confidence
        )
    
    def get_deduplication_summary(self) -> Dict[str, Any]:
        """Get summary of deduplication actions."""
        return {
            "total_merges": len(self.deduplication_log),
            "merge_actions": self.deduplication_log.copy(),
            "similarity_threshold": self.similarity_threshold
        }