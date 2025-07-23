#!/usr/bin/env python3
"""
Setup script for Document Organizer.
"""

from setuptools import setup, find_packages
import os
import re

# Read version from __init__.py
def get_version():
    with open(os.path.join("organizer", "__init__.py"), "r") as f:
        content = f.read()
        match = re.search(r'__version__ = ["\']([^"\']+)["\']', content)
        if match:
            return match.group(1)
    return "1.0.0"

# Read long description from README
def get_long_description():
    with open("README.md", "r", encoding="utf-8") as f:
        return f.read()

# Read requirements
def get_requirements():
    with open("requirements.txt", "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="document-organizer",
    version=get_version(),
    author="Document Organizer Contributors",
    author_email="contributors@document-organizer.com",
    description="A powerful Python CLI tool that processes large document collections using Azure OpenAI GPT-4.1",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/document-organizer",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/document-organizer/issues",
        "Source": "https://github.com/yourusername/document-organizer",
        "Documentation": "https://github.com/yourusername/document-organizer#readme",
        "Changelog": "https://github.com/yourusername/document-organizer/blob/main/CHANGELOG.md",
    },
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Healthcare Industry",
        "Intended Audience :: End Users/Desktop",
        "Intended Audience :: Information Technology",
        "Topic :: Office/Business :: Office Suites",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Text Processing :: General",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Natural Language :: English",
    ],
    python_requires=">=3.8",
    install_requires=get_requirements(),
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
            "safety>=2.0.0",
            "bandit>=1.7.0",
        ],
        "ocr": [
            "pytesseract>=0.3.10",
            "Pillow>=9.0.0",
            "pdf2image>=3.1.0",
        ],
        "performance": [
            "psutil>=5.9.0",
        ],
        "all": [
            "pytesseract>=0.3.10",
            "Pillow>=9.0.0",
            "pdf2image>=3.1.0",
            "psutil>=5.9.0",
            "python-docx>=0.8.11",
            "tqdm>=4.64.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "document-organizer=organizer:main",
            "doc-organizer=organizer:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.json", "*.yml", "*.yaml"],
    },
    zip_safe=False,
    keywords=[
        "document-processing",
        "azure-openai",
        "gpt-4",
        "ocr",
        "medical-records",
        "document-organization",
        "text-processing",
        "ai",
        "nlp",
        "healthcare",
        "automation",
    ],
    platforms=["any"],
    license="MIT",
    test_suite="tests",
    tests_require=[
        "pytest>=7.0.0",
        "pytest-cov>=4.0.0",
        "pytest-mock>=3.10.0",
        "pytest-asyncio>=0.21.0",
    ],
)