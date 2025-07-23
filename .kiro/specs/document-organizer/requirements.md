# Requirements Document

## Introduction

The Document Organizer is a Python-based command-line tool that processes large sets of documents using Azure OpenAI GPT-4.1 with 1M-token context capability. The system is designed to organize and summarize two specific types of document collections: medical records (3000+ pages) and life history documents (career achievements, training, awards). The tool supports multiple file formats, includes OCR capabilities for scanned documents, extracts structured data, performs intelligent deduplication, and outputs organized content in multiple formats with full traceability.

## Requirements

### Requirement 1

**User Story:** As a medical professional, I want to process large collections of medical records through a command-line interface, so that I can quickly organize and summarize patient information from thousands of pages.

#### Acceptance Criteria

1. WHEN the user runs the CLI with `--mode medical` THEN the system SHALL process medical documents and extract medical-specific data fields
2. WHEN processing medical documents THEN the system SHALL extract condition, visit dates, medications, physician, notes, and source file references
3. WHEN the user specifies an input folder THEN the system SHALL process all supported file types (txt, docx, pdf, jpg, png) in that folder
4. WHEN processing is complete THEN the system SHALL output structured medical data in CSV format with all extracted fields

### Requirement 2

**User Story:** As a career counselor or individual, I want to process life history documents through a command-line interface, so that I can organize career achievements, training records, and awards into a comprehensive summary.

#### Acceptance Criteria

1. WHEN the user runs the CLI with `--mode life` THEN the system SHALL process life history documents and extract career-specific data fields
2. WHEN processing life history documents THEN the system SHALL extract role, start date, end date, location, key achievements, and source file references
3. WHEN processing career documents THEN the system SHALL maintain chronological accuracy and preserve all time ranges
4. WHEN processing is complete THEN the system SHALL output structured career data in CSV format with all extracted fields

### Requirement 3

**User Story:** As a user with mixed document formats including scanned documents, I want OCR capabilities integrated into the processing pipeline, so that I can extract text from images and scanned PDFs without manual conversion.

#### Acceptance Criteria

1. WHEN the system encounters image files (jpg, png) THEN it SHALL use Tesseract OCR to extract text content
2. WHEN the system encounters scanned PDF files THEN it SHALL apply OCR processing to extract readable text
3. WHEN OCR processing is applied THEN the system SHALL preserve the original file reference and page numbers where possible
4. WHEN OCR fails or produces low-quality results THEN the system SHALL log the error and continue processing other files

### Requirement 4

**User Story:** As a user processing large document collections, I want the system to use Azure OpenAI GPT-4.1 with parallel processing, so that I can efficiently analyze thousands of pages within reasonable time limits.

#### Acceptance Criteria

1. WHEN the system processes documents THEN it SHALL use Azure OpenAI GPT-4.1 with 1M-token context capability
2. WHEN processing large document sets THEN the system SHALL make parallel GPT calls with up to 10 concurrent requests
3. WHEN input exceeds token limits THEN the system SHALL chunk documents into ~8k token segments using tiktoken
4. WHEN making API calls THEN the system SHALL implement proper async/await patterns for optimal performance
5. WHEN API calls fail THEN the system SHALL implement retry logic with exponential backoff

### Requirement 5

**User Story:** As a user analyzing document collections, I want intelligent deduplication that preserves important details, so that I don't lose critical information while eliminating redundancy.

#### Acceptance Criteria

1. WHEN processing medical records with duplicate conditions THEN the system SHALL merge repeated conditions into single entries while preserving ALL visit dates and notes
2. WHEN processing life history with duplicate roles THEN the system SHALL merge repeated roles while preserving complete date ranges and all achievements
3. WHEN deduplicating entries THEN the system SHALL maintain source file references for all merged content
4. WHEN deduplication occurs THEN the system SHALL log the merge actions for user review

### Requirement 6

**User Story:** As a user who needs comprehensive output options, I want multiple export formats with full traceability, so that I can use the organized data in different contexts and verify source information.

#### Acceptance Criteria

1. WHEN processing is complete THEN the system SHALL generate Markdown summaries in the `output/md/` directory
2. WHEN processing is complete THEN the system SHALL generate DOCX summaries in the `output/docx/` directory
3. WHEN processing is complete THEN the system SHALL generate CSV files with structured data in the `output/csv/` directory
4. WHEN processing is complete THEN the system SHALL save JSON backups of all GPT outputs in the `output/json/` directory
5. WHEN generating CSV output THEN the system SHALL include source file names and page numbers for complete traceability
6. WHEN creating summaries THEN the system SHALL first generate an outline saved as `outline.md`

### Requirement 7

**User Story:** As a user processing large document collections, I want real-time progress feedback with time estimates, so that I can monitor processing status and plan accordingly.

#### Acceptance Criteria

1. WHEN the system begins processing THEN it SHALL display a progress bar using tqdm
2. WHEN processing chunks THEN the system SHALL show current progress and estimated time to completion
3. WHEN processing individual files THEN the system SHALL provide status updates for each major processing step
4. WHEN errors occur THEN the system SHALL display clear error messages without stopping the entire process

### Requirement 8

**User Story:** As a user setting up the system, I want configurable Azure credentials and easy installation, so that I can quickly deploy the tool in my environment.

#### Acceptance Criteria

1. WHEN configuring the system THEN the user SHALL provide Azure credentials via a `config.json` file
2. WHEN the config file is missing or invalid THEN the system SHALL provide clear error messages with setup instructions
3. WHEN installing the system THEN all Python dependencies SHALL be listed in `requirements.txt`
4. WHEN setting up OCR THEN the system SHALL provide clear instructions for Tesseract installation
5. WHEN running the CLI THEN the system SHALL support configurable parameters for input, output, and thread count

### Requirement 9

**User Story:** As a developer or advanced user, I want modular code architecture with clear separation of concerns, so that I can maintain, extend, or customize the system components.

#### Acceptance Criteria

1. WHEN examining the codebase THEN the system SHALL have a clear modular structure with separate utilities for each major function
2. WHEN processing files THEN file loading logic SHALL be isolated in `utils/file_loader.py`
3. WHEN performing OCR THEN OCR functionality SHALL be isolated in `utils/ocr.py`
4. WHEN chunking content THEN token-based chunking SHALL be isolated in `utils/chunker.py`
5. WHEN calling Azure GPT THEN API logic SHALL be isolated in `utils/azure_gpt.py`
6. WHEN processing results THEN merge and deduplication logic SHALL be isolated in `utils/processor.py`
7. WHEN generating output THEN export functionality SHALL be isolated in `utils/output_writer.py`

### Requirement 10

**User Story:** As a user who may need to reprocess data, I want comprehensive logging and backup of all GPT responses, so that I can troubleshoot issues or reprocess data without making additional API calls.

#### Acceptance Criteria

1. WHEN making GPT API calls THEN the system SHALL save raw JSON responses for each chunk processed
2. WHEN saving JSON backups THEN each response SHALL be saved with a unique identifier linking it to source content
3. WHEN errors occur during processing THEN the system SHALL log detailed error information including file names and processing steps
4. WHEN processing is complete THEN the system SHALL provide a summary report of all files processed, errors encountered, and outputs generated