---
name: Bug Report
about: Create a report to help us improve Document Organizer
title: '[BUG] '
labels: ['bug', 'needs-triage']
assignees: ''
---

## 🐛 Bug Description

**Describe the bug**
A clear and concise description of what the bug is.

**Expected behavior**
A clear and concise description of what you expected to happen.

**Actual behavior**
A clear and concise description of what actually happened.

## 🔄 Steps to Reproduce

Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Command used:**
```bash
python organizer.py --mode medical --input ./docs --output ./results
```

## 📋 Environment Information

**System Information:**
- OS: [e.g. Windows 10, macOS 12.0, Ubuntu 20.04]
- Python Version: [e.g. 3.9.7]
- Document Organizer Version: [e.g. 1.0.0]

**Dependencies:**
- Azure OpenAI: [version]
- Tesseract OCR: [version if applicable]
- Other relevant packages: [list versions]

**Configuration:**
- Processing mode: [medical/life]
- Concurrent requests: [number]
- Chunk size: [tokens]
- OCR enabled: [yes/no]

## 📁 Sample Data

**File types processed:**
- [ ] TXT files
- [ ] DOCX files
- [ ] PDF files
- [ ] Image files (JPG/PNG)

**Dataset size:**
- Number of files: [approximate count]
- Total size: [approximate MB/GB]
- Largest file: [approximate size]

## 📝 Error Details

**Error message:**
```
Paste the complete error message here
```

**Log output:**
```
Paste relevant log entries here (remove sensitive information)
```

**Stack trace:**
```
Paste the full stack trace if available
```

## 📸 Screenshots

If applicable, add screenshots to help explain your problem.

## 🔍 Additional Context

**What were you trying to accomplish?**
Describe the task you were performing when the bug occurred.

**Workarounds:**
Have you found any workarounds for this issue?

**Frequency:**
- [ ] This happens every time
- [ ] This happens sometimes
- [ ] This happened once

**Impact:**
- [ ] Blocks all functionality
- [ ] Blocks some functionality
- [ ] Minor inconvenience
- [ ] Cosmetic issue

## 🧪 Debugging Information

**Have you tried:**
- [ ] Running with `--verbose` flag
- [ ] Checking the logs directory
- [ ] Running `--check-deps` command
- [ ] Testing with a smaller dataset
- [ ] Updating to the latest version

**Configuration file (remove sensitive data):**
```json
{
  "azure_openai": {
    "endpoint": "https://your-resource.openai.azure.com/",
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

## 📋 Checklist

Before submitting, please ensure:

- [ ] I have searched existing issues for similar problems
- [ ] I have included all relevant information above
- [ ] I have removed any sensitive information from logs/config
- [ ] I have tested with the latest version
- [ ] I have included steps to reproduce the issue

## 🏷️ Labels

Please add appropriate labels:
- **Priority**: `low`, `medium`, `high`, `critical`
- **Component**: `cli`, `ocr`, `chunking`, `api`, `output`, `config`
- **OS**: `windows`, `macos`, `linux`

---

**Note:** Issues without sufficient information may be closed. Please provide as much detail as possible to help us resolve the issue quickly.