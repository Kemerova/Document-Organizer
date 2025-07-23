#!/usr/bin/env python3
"""
Document Organizer - Main CLI application.
Processes large document collections using Azure OpenAI GPT-4.1 with OCR capabilities.
"""

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

from utils.config import ConfigLoader, ConfigurationError
from utils.file_loader import FileLoader
try:
    from utils.ocr import OCRProcessor, is_ocr_available
except ImportError:
    # Fallback if OCR module has issues
    class OCRProcessor:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("OCR not available")
        def process_file(self, *args, **kwargs):
            return "", 0.0, [], False
    
    def is_ocr_available():
        return False
from utils.chunker import TokenAwareChunker, is_tiktoken_available
try:
    from utils.azure_gpt import AzureGPTClient
except ImportError:
    # Fallback if aiohttp has compatibility issues
    class AzureGPTClient:
        def __init__(self, config):
            self.config = config
        async def batch_process_chunks(self, chunks, mode, callback=None):
            return []
        async def generate_outline(self, summaries):
            return {"outline": {"title": "Processing not available", "sections": []}}
        def get_statistics(self):
            return {"total_requests": 0, "successful_requests": 0, "success_rate": 0, "total_tokens_used": 0}
from utils.processor import DataProcessor
from utils.output_writer import OutputWriter, is_docx_available


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f"logs/organizer_{int(time.time())}.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from external libraries
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Document Organizer - Process large document collections with Azure OpenAI GPT-4.1",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process medical records
  python organizer.py --mode medical --input ./medical_docs --output ./results

  # Process life history documents with custom settings
  python organizer.py --mode life --input ./career_docs --threads 5 --config custom_config.json

  # Generate configuration template
  python organizer.py --create-config

  # Check system dependencies
  python organizer.py --check-deps
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['medical', 'life'],
        help='Processing mode: medical records or life history documents'
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        help='Input directory containing documents to process'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='output',
        help='Output directory for generated files (default: output)'
    )
    
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='config.json',
        help='Configuration file path (default: config.json)'
    )
    
    parser.add_argument(
        '--threads', '-t',
        type=int,
        help='Maximum concurrent API requests (overrides config)'
    )
    
    parser.add_argument(
        '--chunk-size',
        type=int,
        help='Token chunk size (overrides config)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--create-config',
        action='store_true',
        help='Create configuration template and exit'
    )
    
    parser.add_argument(
        '--check-deps',
        action='store_true',
        help='Check system dependencies and exit'
    )
    
    parser.add_argument(
        '--no-ocr',
        action='store_true',
        help='Disable OCR processing for images and scanned PDFs'
    )
    
    return parser.parse_args()


def check_dependencies() -> Dict[str, bool]:
    """Check system dependencies."""
    deps = {
        'tiktoken': is_tiktoken_available(),
        'ocr': is_ocr_available(),
        'docx': is_docx_available(),
        'tqdm': TQDM_AVAILABLE
    }
    
    print("System Dependencies Check:")
    print("=" * 40)
    
    for dep, available in deps.items():
        status = "✓ Available" if available else "✗ Missing"
        print(f"{dep:15} {status}")
    
    if not deps['tiktoken']:
        print("\nTo install tiktoken: pip install tiktoken")
    
    if not deps['ocr']:
        print("\nTo install OCR dependencies:")
        print("  pip install pytesseract pillow pdf2image")
        print("  Also install Tesseract OCR system package")
    
    if not deps['docx']:
        print("\nTo install DOCX support: pip install python-docx")
    
    if not deps['tqdm']:
        print("\nTo install progress bars: pip install tqdm")
    
    return deps


class ProgressTracker:
    """Progress tracking with tqdm or fallback."""
    
    def __init__(self, total: int, description: str):
        self.total = total
        self.current = 0
        self.description = description
        
        if TQDM_AVAILABLE:
            self.pbar = tqdm(total=total, desc=description, unit="items")
        else:
            self.pbar = None
            print(f"Starting {description} (0/{total})")
    
    def update(self, increment: int = 1):
        """Update progress."""
        self.current += increment
        
        if self.pbar:
            self.pbar.update(increment)
        else:
            print(f"{self.description}: {self.current}/{self.total}")
    
    def close(self):
        """Close progress tracker."""
        if self.pbar:
            self.pbar.close()
        else:
            print(f"Completed {self.description}: {self.current}/{self.total}")


async def process_documents(args: argparse.Namespace) -> None:
    """Main document processing pipeline."""
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = ConfigLoader.load_config(args.config)
        
        # Override config with command line arguments
        if args.threads:
            config.processing.max_concurrent_requests = args.threads
        if args.chunk_size:
            config.processing.chunk_size_tokens = args.chunk_size
        
        logger.info(f"Configuration loaded: {args.threads or config.processing.max_concurrent_requests} threads, "
                   f"{args.chunk_size or config.processing.chunk_size_tokens} token chunks")
        
        # Initialize components
        file_loader = FileLoader()
        output_writer = OutputWriter(args.output)
        
        # Initialize OCR if available and not disabled
        ocr_processor = None
        if not args.no_ocr and is_ocr_available():
            try:
                ocr_processor = OCRProcessor()
                logger.info("OCR processor initialized")
            except Exception as e:
                logger.warning(f"OCR initialization failed: {e}")
        
        # Initialize chunker
        if not is_tiktoken_available():
            raise RuntimeError("tiktoken is required but not available. Install with: pip install tiktoken")
        
        chunker = TokenAwareChunker(
            max_tokens=config.processing.chunk_size_tokens
        )
        
        # Initialize GPT client
        gpt_client = AzureGPTClient(config)
        
        # Initialize data processor
        data_processor = DataProcessor()
        
        # Phase 1: File Discovery
        logger.info("Phase 1: Discovering files...")
        input_path = Path(args.input)
        if not input_path.exists():
            raise FileNotFoundError(f"Input directory not found: {args.input}")
        
        discovered_files = file_loader.discover_files(str(input_path))
        logger.info(f"Discovered {len(discovered_files)} files")
        
        if not discovered_files:
            logger.warning("No supported files found in input directory")
            return
        
        # Phase 2: File Loading and OCR
        logger.info("Phase 2: Loading files and applying OCR...")
        documents = []
        
        progress = ProgressTracker(len(discovered_files), "Loading files")
        
        for file_path in discovered_files:
            try:
                # Load file content
                doc_content = file_loader.load_file(file_path)
                
                # Apply OCR if needed and available
                if ocr_processor and not doc_content['content'].strip():
                    try:
                        ocr_text, confidence, pages, ocr_applied = ocr_processor.process_file(file_path)
                        if ocr_applied and ocr_text.strip():
                            doc_content['content'] = ocr_text
                            doc_content['ocr_applied'] = True
                            doc_content['extraction_confidence'] = confidence
                            logger.info(f"OCR applied to {file_path}: {confidence:.2f} confidence")
                    except Exception as e:
                        logger.warning(f"OCR failed for {file_path}: {e}")
                
                if doc_content['content'].strip():
                    documents.append(doc_content)
                else:
                    logger.warning(f"No content extracted from {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
            
            progress.update()
        
        progress.close()
        
        if not documents:
            logger.error("No documents with content were loaded")
            return
        
        logger.info(f"Loaded {len(documents)} documents with content")
        
        # Phase 3: Content Chunking
        logger.info("Phase 3: Chunking content...")
        chunks = chunker.chunk_content(documents)
        
        chunk_summary = chunker.get_chunk_summary(chunks)
        logger.info(f"Created {chunk_summary['total_chunks']} chunks with "
                   f"{chunk_summary['total_tokens']} total tokens")
        
        # Validate chunks
        warnings = chunker.validate_chunks(chunks)
        for warning in warnings:
            logger.warning(warning)
        
        # Phase 4: GPT Processing
        logger.info("Phase 4: Processing with Azure OpenAI GPT...")
        
        def progress_callback(completed: int, total: int):
            if not hasattr(progress_callback, 'tracker'):
                progress_callback.tracker = ProgressTracker(total, "Processing chunks")
            progress_callback.tracker.update(completed - getattr(progress_callback, 'last_completed', 0))
            progress_callback.last_completed = completed
        
        responses = await gpt_client.batch_process_chunks(chunks, args.mode, progress_callback)
        
        if hasattr(progress_callback, 'tracker'):
            progress_callback.tracker.close()
        
        # Log GPT statistics
        stats = gpt_client.get_statistics()
        logger.info(f"GPT processing complete: {stats['successful_requests']}/{stats['total_requests']} successful, "
                   f"{stats['total_tokens_used']} tokens used")
        
        # Phase 5: Data Consolidation
        logger.info("Phase 5: Consolidating and deduplicating data...")
        consolidated_data = data_processor.consolidate_responses(responses, args.mode)
        
        dedup_summary = data_processor.get_deduplication_summary()
        logger.info(f"Deduplication complete: {dedup_summary['total_merges']} merges performed")
        
        # Phase 6: Outline Generation
        logger.info("Phase 6: Generating document outline...")
        outline_data = await gpt_client.generate_outline(consolidated_data.summaries)
        
        # Phase 7: Output Generation
        logger.info("Phase 7: Generating output files...")
        generated_files = output_writer.write_all_formats(
            consolidated_data, args.mode, outline_data, responses
        )
        
        # Summary
        total_files = sum(len(files) for files in generated_files.values())
        logger.info(f"Processing complete! Generated {total_files} output files:")
        
        for format_type, files in generated_files.items():
            if files:
                print(f"\n{format_type.upper()} files:")
                for file_path in files:
                    print(f"  - {file_path}")
        
        print(f"\nProcessing Summary:")
        print(f"  Input files: {len(discovered_files)}")
        print(f"  Documents processed: {len(documents)}")
        print(f"  Chunks created: {len(chunks)}")
        print(f"  GPT requests: {stats['total_requests']}")
        print(f"  Success rate: {stats['success_rate']:.1f}%")
        print(f"  Tokens used: {stats['total_tokens_used']:,}")
        
        if args.mode == 'medical':
            print(f"  Medical records: {len(consolidated_data.medical_records)}")
        else:
            print(f"  Life history records: {len(consolidated_data.life_history_records)}")
        
        print(f"  Deduplication merges: {dedup_summary['total_merges']}")
        print(f"  Output files: {total_files}")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise


def main() -> None:
    """Main entry point."""
    args = parse_arguments()
    
    # Handle special commands
    if args.create_config:
        ConfigLoader.create_template()
        return
    
    if args.check_deps:
        deps = check_dependencies()
        sys.exit(0 if all(deps.values()) else 1)
    
    # Validate required arguments
    if not args.mode:
        print("Error: --mode is required (medical or life)")
        sys.exit(1)
    
    if not args.input:
        print("Error: --input directory is required")
        sys.exit(1)
    
    # Set up logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        logger.info("Document Organizer starting...")
        logger.info(f"Mode: {args.mode}, Input: {args.input}, Output: {args.output}")
        
        # Run async processing
        asyncio.run(process_documents(args))
        
        logger.info("Document Organizer completed successfully")
        
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
        sys.exit(1)
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()