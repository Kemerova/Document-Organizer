#!/usr/bin/env python3
"""
Document Organizer Demo - Shows the complete codebase structure.
This demo version works without external dependencies for demonstration purposes.
"""

import argparse
import json
import os
from pathlib import Path

def show_codebase_structure():
    """Display the complete codebase structure."""
    print("Document Organizer - Complete Codebase Structure")
    print("=" * 50)
    
    # Show directory structure
    print("\nProject Structure:")
    structure = """
document-organizer/
├── organizer.py              # Main CLI application
├── requirements.txt          # Python dependencies
├── README.md                # Complete documentation
├── config.json.template     # Configuration template
├── organizer/               # Main package
│   └── __init__.py
├── utils/                   # Utility modules
│   ├── __init__.py
│   ├── config.py           # Configuration management
│   ├── models.py           # Data models
│   ├── file_loader.py      # Multi-format file loading
│   ├── ocr.py              # OCR processing
│   ├── chunker.py          # Token-aware chunking
│   ├── azure_gpt.py        # Azure OpenAI client
│   ├── processor.py        # Data consolidation
│   └── output_writer.py    # Multi-format output
├── tests/                  # Unit tests
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_models.py
│   ├── test_file_loader.py
│   └── (other test files)
├── output/                 # Generated output
│   ├── md/                # Markdown summaries
│   ├── docx/              # Word documents
│   ├── csv/               # Structured data
│   └── json/              # Raw data backup
└── logs/                  # Processing logs
"""
    print(structure)
    
    # Show key features
    print("\nKey Features Implemented:")
    features = [
        "✓ Multi-format file support (TXT, DOCX, PDF, JPG, PNG)",
        "✓ OCR integration with Tesseract",
        "✓ Azure OpenAI GPT-4.1 integration",
        "✓ Token-aware content chunking",
        "✓ Parallel async processing",
        "✓ Intelligent deduplication",
        "✓ Multi-format output (MD, DOCX, CSV, JSON)",
        "✓ Progress tracking and logging",
        "✓ Comprehensive error handling",
        "✓ Full source traceability",
        "✓ Medical and life history modes",
        "✓ CLI interface with argument parsing",
        "✓ Configuration management",
        "✓ Unit test coverage"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print(f"\nTotal Files Implemented: {count_files()}")
    print(f"Total Lines of Code: {count_lines()}")

def count_files():
    """Count implementation files."""
    files = [
        "organizer.py", "requirements.txt", "README.md", "config.json.template",
        "organizer/__init__.py", "utils/__init__.py", "utils/config.py",
        "utils/models.py", "utils/file_loader.py", "utils/ocr.py",
        "utils/chunker.py", "utils/azure_gpt.py", "utils/processor.py",
        "utils/output_writer.py", "tests/__init__.py", "tests/test_config.py",
        "tests/test_models.py", "tests/test_file_loader.py"
    ]
    return len([f for f in files if Path(f).exists()])

def count_lines():
    """Count total lines of code."""
    total_lines = 0
    for root, dirs, files in os.walk("."):
        for file in files:
            if file.endswith(".py") and not file.startswith("demo"):
                try:
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        total_lines += len(f.readlines())
                except:
                    pass
    return total_lines

def show_usage_examples():
    """Show usage examples."""
    print("\nUsage Examples:")
    print("-" * 30)
    
    examples = [
        "# Create configuration template",
        "python organizer.py --create-config",
        "",
        "# Check system dependencies", 
        "python organizer.py --check-deps",
        "",
        "# Process medical records",
        "python organizer.py --mode medical --input ./medical_docs --output ./results",
        "",
        "# Process life history with custom settings",
        "python organizer.py --mode life --input ./career_docs --threads 5 --verbose",
        "",
        "# Run with custom configuration",
        "python organizer.py --mode medical --input ./docs --config custom_config.json"
    ]
    
    for example in examples:
        print(example)

def show_requirements():
    """Show requirements and dependencies."""
    print("\nDependencies:")
    print("-" * 20)
    
    try:
        with open("requirements.txt", 'r') as f:
            requirements = f.read()
        print(requirements)
    except FileNotFoundError:
        print("requirements.txt not found")

def main():
    """Main demo function."""
    parser = argparse.ArgumentParser(description="Document Organizer Demo")
    parser.add_argument('--structure', action='store_true', help='Show codebase structure')
    parser.add_argument('--usage', action='store_true', help='Show usage examples')
    parser.add_argument('--requirements', action='store_true', help='Show requirements')
    parser.add_argument('--all', action='store_true', help='Show everything')
    
    args = parser.parse_args()
    
    if args.all or not any([args.structure, args.usage, args.requirements]):
        show_codebase_structure()
        show_usage_examples()
        show_requirements()
    else:
        if args.structure:
            show_codebase_structure()
        if args.usage:
            show_usage_examples()
        if args.requirements:
            show_requirements()

if __name__ == '__main__':
    main()