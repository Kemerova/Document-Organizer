# Contributing to Document Organizer

Thank you for your interest in contributing to Document Organizer! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Issues

1. **Search existing issues** first to avoid duplicates
2. **Use issue templates** when creating new issues
3. **Provide detailed information** including:
   - Operating system and Python version
   - Steps to reproduce the issue
   - Expected vs actual behavior
   - Error messages and logs
   - Sample files (if applicable, remove sensitive data)

### Suggesting Features

1. **Check the roadmap** in issues to see if it's already planned
2. **Use the feature request template**
3. **Explain the use case** and why it would be valuable
4. **Consider implementation complexity** and maintenance burden

### Code Contributions

1. **Fork the repository** and create a feature branch
2. **Follow coding standards** (see below)
3. **Write tests** for new functionality
4. **Update documentation** as needed
5. **Submit a pull request** with clear description

## 🛠 Development Setup

### Prerequisites

- Python 3.8 or higher
- Git
- Azure OpenAI account (for testing)
- Tesseract OCR (optional, for OCR features)

### Local Development

1. **Clone your fork**:
   ```bash
   git clone https://github.com/yourusername/document-organizer.git
   cd document-organizer
   ```

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Set up configuration**:
   ```bash
   python organizer.py --create-config
   # Edit config.json with your Azure OpenAI credentials
   ```

5. **Run tests**:
   ```bash
   pytest tests/ -v
   ```

### Development Workflow

1. **Create feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** following coding standards

3. **Run tests and linting**:
   ```bash
   pytest tests/
   flake8 .
   black .
   mypy .
   ```

4. **Commit changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create PR**:
   ```bash
   git push origin feature/your-feature-name
   ```

## 📝 Coding Standards

### Python Style Guide

- **Follow PEP 8** for Python code style
- **Use Black** for code formatting
- **Use type hints** for function parameters and return values
- **Write docstrings** for all public functions and classes
- **Keep functions focused** and under 50 lines when possible

### Code Organization

- **Modular design**: Keep related functionality in separate modules
- **Clear naming**: Use descriptive names for variables, functions, and classes
- **Error handling**: Use appropriate exception types and provide helpful messages
- **Logging**: Use the logging module instead of print statements

### Example Code Style

```python
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

def process_documents(file_paths: List[str], 
                     mode: str = "medical") -> Optional[Dict[str, Any]]:
    """
    Process a list of document files.
    
    Args:
        file_paths: List of file paths to process
        mode: Processing mode ('medical' or 'life')
        
    Returns:
        Dictionary with processing results or None if failed
        
    Raises:
        ValueError: If mode is not supported
        FileNotFoundError: If files don't exist
    """
    if mode not in ["medical", "life"]:
        raise ValueError(f"Unsupported mode: {mode}")
    
    logger.info(f"Processing {len(file_paths)} files in {mode} mode")
    
    # Implementation here
    return results
```

## 🧪 Testing Guidelines

### Test Structure

- **Unit tests**: Test individual functions and classes
- **Integration tests**: Test component interactions
- **End-to-end tests**: Test complete workflows
- **Performance tests**: Test with large datasets

### Writing Tests

```python
import unittest
from unittest.mock import Mock, patch
from utils.your_module import YourClass

class TestYourClass(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures."""
        self.instance = YourClass()
    
    def test_your_function(self):
        """Test your function with valid input."""
        result = self.instance.your_function("test_input")
        self.assertEqual(result, "expected_output")
    
    def test_your_function_error_case(self):
        """Test your function error handling."""
        with self.assertRaises(ValueError):
            self.instance.your_function("invalid_input")
```

### Test Coverage

- **Aim for 80%+ coverage** for new code
- **Test error conditions** and edge cases
- **Mock external dependencies** (APIs, file system)
- **Use descriptive test names** that explain what's being tested

## 📚 Documentation

### Code Documentation

- **Docstrings**: Use Google-style docstrings for all public APIs
- **Type hints**: Provide type annotations for better IDE support
- **Comments**: Explain complex logic, not obvious code
- **Examples**: Include usage examples in docstrings

### User Documentation

- **Update README.md** for new features
- **Add troubleshooting** for common issues
- **Include examples** for new functionality
- **Update CLI help** text when adding options

## 🔄 Pull Request Process

### Before Submitting

1. **Ensure tests pass**: All existing and new tests must pass
2. **Update documentation**: Include relevant documentation updates
3. **Follow commit conventions**: Use conventional commit messages
4. **Rebase if needed**: Keep commit history clean

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
```

### Review Process

1. **Automated checks** must pass (CI/CD)
2. **Code review** by maintainers
3. **Testing** on different platforms if needed
4. **Approval** and merge by maintainers

## 🏗 Architecture Guidelines

### Adding New Features

1. **Design first**: Consider impact on existing architecture
2. **Modular approach**: Keep features in separate modules
3. **Configuration**: Make features configurable when appropriate
4. **Error handling**: Implement comprehensive error handling
5. **Testing**: Include comprehensive test coverage

### Performance Considerations

- **Memory efficiency**: Consider memory usage for large datasets
- **Async operations**: Use async/await for I/O operations
- **Caching**: Implement caching where appropriate
- **Profiling**: Profile performance-critical code

## 🐛 Debugging Guidelines

### Common Issues

1. **Configuration errors**: Check config.json format and credentials
2. **Dependency issues**: Verify all requirements are installed
3. **OCR problems**: Ensure Tesseract is properly installed
4. **API errors**: Check Azure OpenAI service status and limits

### Debugging Tools

- **Logging**: Use verbose logging (`--verbose` flag)
- **Debugger**: Use Python debugger (pdb) for complex issues
- **Profiling**: Use cProfile for performance issues
- **Testing**: Write tests to reproduce issues

## 📋 Release Process

### Version Numbering

- **Semantic versioning**: MAJOR.MINOR.PATCH
- **Breaking changes**: Increment MAJOR version
- **New features**: Increment MINOR version
- **Bug fixes**: Increment PATCH version

### Release Checklist

1. **Update version** in relevant files
2. **Update CHANGELOG.md** with new features and fixes
3. **Run full test suite** on multiple platforms
4. **Update documentation** as needed
5. **Create release** with detailed notes

## 🤔 Questions?

- **Check existing issues** and documentation first
- **Join discussions** in GitHub issues
- **Contact maintainers** for complex questions
- **Be patient and respectful** in all interactions

## 📜 Code of Conduct

- **Be respectful** and inclusive
- **Focus on constructive feedback**
- **Help others learn and grow**
- **Follow GitHub's community guidelines**

Thank you for contributing to Document Organizer! 🎉