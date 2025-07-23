# Document Organizer

A powerful Python CLI tool that processes large document collections using Azure OpenAI GPT-4.1 with 1M-token context capability. Designed to organize and summarize medical records and life history documents with OCR support, intelligent deduplication, and multi-format output.

## Features

- **Multi-format Support**: Process TXT, DOCX, PDF, JPG, PNG files
- **OCR Integration**: Extract text from images and scanned PDFs using Tesseract
- **Azure OpenAI GPT-4.1**: Leverage 1M-token context for comprehensive analysis
- **Parallel Processing**: Configurable concurrent API requests for optimal performance
- **Intelligent Deduplication**: Merge similar records while preserving all details
- **Multiple Output Formats**: Generate Markdown, DOCX, CSV, and JSON outputs
- **Full Traceability**: Track all data back to source files and page numbers
- **Progress Tracking**: Real-time progress bars and ETA calculations

## Installation

### Prerequisites

1. **Python 3.8+** is required
2. **Azure OpenAI** account with GPT-4.1 deployment
3. **Tesseract OCR** for image processing (optional but recommended)

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Install Tesseract OCR

#### Windows
1. Download from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
2. Install and add to PATH
3. Or use: `choco install tesseract` (if using Chocolatey)

#### macOS
```bash
brew install tesseract
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

## Configuration

### 1. Create Configuration File

Generate a configuration template:
```bash
python organizer.py --create-config
```

This creates `config.json` with the following structure:

```json
{
  "azure_openai": {
    "endpoint": "https://your-resource.openai.azure.com/",
    "api_key": "your-api-key-here",
    "deployment_name": "gpt-4-1106-preview",
    "api_version": "2024-02-15-preview"
  },
  "processing": {
    "max_concurrent_requests": 10,
    "chunk_size_tokens": 8000,
    "retry_attempts": 3
  }
}
```

### 2. Configure Azure OpenAI

1. Create an Azure OpenAI resource in the Azure portal
2. Deploy a GPT-4.1 model (e.g., `gpt-4-1106-preview`)
3. Get your endpoint URL and API key
4. Update `config.json` with your credentials

### 3. Verify Setup

Check that all dependencies are installed:
```bash
python organizer.py --check-deps
```

## Usage

### Basic Usage

#### Process Medical Records
```bash
python organizer.py --mode medical --input ./medical_docs --output ./results
```

#### Process Life History Documents
```bash
python organizer.py --mode life --input ./career_docs --output ./results
```

### Advanced Options

```bash
python organizer.py \
  --mode medical \
  --input ./documents \
  --output ./results \
  --config custom_config.json \
  --threads 5 \
  --chunk-size 6000 \
  --verbose
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--mode` | Processing mode: `medical` or `life` | Required |
| `--input, -i` | Input directory with documents | Required |
| `--output, -o` | Output directory for results | `output` |
| `--config, -c` | Configuration file path | `config.json` |
| `--threads, -t` | Max concurrent API requests | From config |
| `--chunk-size` | Token chunk size | From config |
| `--verbose, -v` | Enable verbose logging | False |
| `--no-ocr` | Disable OCR processing | False |
| `--create-config` | Create config template and exit | - |
| `--check-deps` | Check dependencies and exit | - |

## Processing Modes

### Medical Mode (`--mode medical`)

Extracts and organizes:
- Medical conditions and diagnoses
- Visit dates and appointment history
- Medications and prescriptions
- Physician and facility information
- Clinical notes and observations

**Output includes:**
- Chronological medical timeline
- Medication history with dates
- Physician contact information
- Source file references for verification

### Life History Mode (`--mode life`)

Extracts and organizes:
- Career roles and positions
- Employment dates and duration
- Organizations and locations
- Key achievements and responsibilities
- Education and training records

**Output includes:**
- Chronological career timeline
- Achievement summaries by role
- Skills and competency tracking
- Source file references for verification

## Output Formats

The tool generates multiple output formats in organized directories:

```
output/
├── md/                 # Markdown summaries
│   ├── outline_medical_20240115_143022.md
│   └── medical_summary_20240115_143022.md
├── docx/               # Word documents
│   └── medical_summary_20240115_143022.docx
├── csv/                # Structured data
│   └── medical_records_20240115_143022.csv
└── json/               # Raw data and metadata
    ├── raw_responses_medical_20240115_143022.json
    └── processing_metadata_medical_20240115_143022.json
```

### Output Contents

- **Markdown**: Human-readable summaries with full details
- **DOCX**: Professional formatted documents for sharing
- **CSV**: Structured data for analysis and import
- **JSON**: Raw GPT responses and processing metadata for backup

## Performance and Scalability

### Recommended Settings

| Document Count | Threads | Chunk Size | Expected Time |
|----------------|---------|------------|---------------|
| 1-100 files | 5 | 8000 | 5-15 minutes |
| 100-500 files | 10 | 8000 | 15-45 minutes |
| 500-1000 files | 15 | 6000 | 45-90 minutes |
| 1000+ files | 20 | 6000 | 1-3 hours |

### Token Usage Estimation

- **Medical documents**: ~500-1000 tokens per page
- **Life history documents**: ~300-800 tokens per page
- **API response**: ~200-500 tokens per chunk
- **Total cost**: Varies by Azure OpenAI pricing tier

## Troubleshooting

### Common Issues

#### Configuration Errors
```
Error: Configuration file not found: config.json
```
**Solution**: Run `python organizer.py --create-config` to generate template

#### OCR Issues
```
Error: Tesseract OCR not found
```
**Solution**: Install Tesseract OCR system package (see Installation section)

#### API Errors
```
Error: Invalid Azure OpenAI API key
```
**Solution**: Verify credentials in Azure portal and update config.json

#### Memory Issues
```
Error: Out of memory during processing
```
**Solution**: Reduce `--chunk-size` or `--threads` parameters

### Debug Mode

Enable verbose logging for detailed troubleshooting:
```bash
python organizer.py --mode medical --input ./docs --verbose
```

Logs are saved to `logs/organizer_[timestamp].log`

### Performance Optimization

1. **Adjust concurrency**: Start with 5 threads, increase gradually
2. **Optimize chunk size**: Smaller chunks = more API calls but better parallelism
3. **Use SSD storage**: Faster file I/O improves overall performance
4. **Monitor API limits**: Azure OpenAI has rate limits per deployment

## File Format Support

| Format | Read Support | OCR Support | Notes |
|--------|--------------|-------------|-------|
| `.txt` | ✅ | N/A | UTF-8 encoding detection |
| `.docx` | ✅ | N/A | Full text and metadata |
| `.pdf` | ✅ | ✅ | Text extraction + OCR for scanned |
| `.jpg/.jpeg` | ✅ | ✅ | Tesseract OCR required |
| `.png` | ✅ | ✅ | Tesseract OCR required |
| `.tiff` | ✅ | ✅ | Tesseract OCR required |

## Data Privacy and Security

- **Local Processing**: All documents processed locally before API calls
- **No Data Retention**: Azure OpenAI doesn't retain your data
- **Secure Credentials**: API keys stored in local config file only
- **Audit Trail**: Complete processing logs for compliance
- **Source Traceability**: All outputs linked to original files

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite: `pytest`
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
1. Check the troubleshooting section above
2. Review logs in the `logs/` directory
3. Create an issue on GitHub with:
   - Command used
   - Error message
   - Log file contents (remove sensitive data)
   - System information

## Changelog

### Version 1.0.0
- Initial release
- Medical and life history processing modes
- OCR support for images and scanned PDFs
- Multi-format output generation
- Azure OpenAI GPT-4.1 integration
- Intelligent deduplication
- Progress tracking and error handling