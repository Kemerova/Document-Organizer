#!/bin/bash

# GitHub Setup Script for Document Organizer
# This script automates the initial GitHub repository setup

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_NAME="document-organizer"
REPO_DESCRIPTION="A powerful Python CLI tool that processes large document collections using Azure OpenAI GPT-4.1"
DEFAULT_BRANCH="main"

# Functions
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Document Organizer GitHub Setup${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
}

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    print_step "Checking prerequisites..."
    
    # Check if git is installed
    if ! command -v git &> /dev/null; then
        print_error "Git is not installed. Please install Git first."
        exit 1
    fi
    
    # Check if gh CLI is installed (optional but recommended)
    if command -v gh &> /dev/null; then
        print_info "GitHub CLI detected. Will use for enhanced setup."
        GH_CLI_AVAILABLE=true
    else
        print_warning "GitHub CLI not found. Some features will be limited."
        print_info "Install with: brew install gh (macOS) or visit https://cli.github.com"
        GH_CLI_AVAILABLE=false
    fi
    
    # Check if we're in the right directory
    if [ ! -f "organizer.py" ]; then
        print_error "Please run this script from the Document Organizer root directory."
        exit 1
    fi
    
    print_info "Prerequisites check completed."
    echo
}

get_user_input() {
    print_step "Getting user configuration..."
    
    # Get GitHub username
    if [ "$GH_CLI_AVAILABLE" = true ]; then
        GITHUB_USERNAME=$(gh api user --jq '.login' 2>/dev/null || echo "")
    fi
    
    if [ -z "$GITHUB_USERNAME" ]; then
        read -p "Enter your GitHub username: " GITHUB_USERNAME
    else
        print_info "Detected GitHub username: $GITHUB_USERNAME"
        read -p "Use this username? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            read -p "Enter your GitHub username: " GITHUB_USERNAME
        fi
    fi
    
    # Confirm repository name
    read -p "Repository name [$REPO_NAME]: " INPUT_REPO_NAME
    REPO_NAME=${INPUT_REPO_NAME:-$REPO_NAME}
    
    # Repository visibility
    read -p "Make repository public? (y/n) [y]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        REPO_VISIBILITY="private"
    else
        REPO_VISIBILITY="public"
    fi
    
    print_info "Configuration:"
    print_info "  Username: $GITHUB_USERNAME"
    print_info "  Repository: $REPO_NAME"
    print_info "  Visibility: $REPO_VISIBILITY"
    echo
}

initialize_git() {
    print_step "Initializing Git repository..."
    
    # Initialize git if not already done
    if [ ! -d ".git" ]; then
        git init
        print_info "Git repository initialized."
    else
        print_info "Git repository already exists."
    fi
    
    # Set default branch
    git branch -M $DEFAULT_BRANCH
    
    # Add all files
    git add .
    
    # Check if there are changes to commit
    if git diff --staged --quiet; then
        print_info "No changes to commit."
    else
        # Create initial commit
        git commit -m "feat: initial release of Document Organizer v1.0.0

- Complete implementation with all 15 tasks completed
- Multi-format document processing (TXT, DOCX, PDF, images)
- Azure OpenAI GPT-4.1 integration with 1M-token context
- OCR support with Tesseract integration
- Intelligent deduplication and data consolidation
- Multi-format output (Markdown, DOCX, CSV, JSON)
- Comprehensive error handling and recovery
- Performance monitoring and optimization
- Production-ready with 80+ unit tests
- Complete documentation and setup guides"
        
        print_info "Initial commit created."
    fi
    
    echo
}

create_github_repo() {
    print_step "Creating GitHub repository..."
    
    if [ "$GH_CLI_AVAILABLE" = true ]; then
        # Use GitHub CLI to create repository
        gh repo create "$GITHUB_USERNAME/$REPO_NAME" \
            --description "$REPO_DESCRIPTION" \
            --$REPO_VISIBILITY \
            --clone=false \
            --confirm
        
        print_info "Repository created using GitHub CLI."
    else
        print_warning "GitHub CLI not available. Please create the repository manually:"
        print_info "1. Go to https://github.com/new"
        print_info "2. Repository name: $REPO_NAME"
        print_info "3. Description: $REPO_DESCRIPTION"
        print_info "4. Visibility: $REPO_VISIBILITY"
        print_info "5. Don't initialize with README, .gitignore, or license"
        print_info "6. Click 'Create repository'"
        echo
        read -p "Press Enter after creating the repository..."
    fi
    
    echo
}

setup_remote_and_push() {
    print_step "Setting up remote and pushing code..."
    
    # Add remote origin
    REPO_URL="https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
    
    # Check if remote already exists
    if git remote get-url origin &> /dev/null; then
        print_info "Remote origin already exists. Updating URL..."
        git remote set-url origin "$REPO_URL"
    else
        git remote add origin "$REPO_URL"
        print_info "Remote origin added: $REPO_URL"
    fi
    
    # Push to GitHub
    print_info "Pushing code to GitHub..."
    git push -u origin $DEFAULT_BRANCH
    
    print_info "Code successfully pushed to GitHub!"
    echo
}

configure_repository() {
    print_step "Configuring repository settings..."
    
    if [ "$GH_CLI_AVAILABLE" = true ]; then
        # Enable issues and wiki
        gh repo edit "$GITHUB_USERNAME/$REPO_NAME" \
            --enable-issues \
            --enable-wiki \
            --delete-branch-on-merge
        
        print_info "Repository settings configured."
        
        # Add topics
        gh repo edit "$GITHUB_USERNAME/$REPO_NAME" \
            --add-topic python \
            --add-topic cli \
            --add-topic azure-openai \
            --add-topic gpt-4 \
            --add-topic document-processing \
            --add-topic ocr \
            --add-topic medical-records \
            --add-topic healthcare \
            --add-topic automation \
            --add-topic ai \
            --add-topic nlp \
            --add-topic text-processing
        
        print_info "Repository topics added."
    else
        print_warning "Manual configuration required:"
        print_info "1. Go to https://github.com/$GITHUB_USERNAME/$REPO_NAME/settings"
        print_info "2. Enable Issues and Wiki"
        print_info "3. Add topics: python, cli, azure-openai, gpt-4, document-processing, ocr"
        print_info "4. Set up branch protection rules for main branch"
    fi
    
    echo
}

create_first_release() {
    print_step "Creating first release..."
    
    if [ "$GH_CLI_AVAILABLE" = true ]; then
        # Create release
        gh release create v1.0.0 \
            --title "Document Organizer v1.0.0 - Initial Release" \
            --notes-file CHANGELOG.md \
            --latest
        
        print_info "Release v1.0.0 created successfully!"
    else
        print_warning "Manual release creation required:"
        print_info "1. Go to https://github.com/$GITHUB_USERNAME/$REPO_NAME/releases"
        print_info "2. Click 'Create a new release'"
        print_info "3. Tag version: v1.0.0"
        print_info "4. Release title: Document Organizer v1.0.0 - Initial Release"
        print_info "5. Copy description from CHANGELOG.md"
        print_info "6. Mark as latest release"
    fi
    
    echo
}

setup_branch_protection() {
    print_step "Setting up branch protection..."
    
    if [ "$GH_CLI_AVAILABLE" = true ]; then
        # Note: Branch protection via CLI requires additional permissions
        print_warning "Branch protection setup requires admin permissions."
        print_info "Please set up branch protection manually:"
    else
        print_warning "Manual branch protection setup required:"
    fi
    
    print_info "1. Go to https://github.com/$GITHUB_USERNAME/$REPO_NAME/settings/branches"
    print_info "2. Add rule for 'main' branch"
    print_info "3. Enable: Require pull request reviews"
    print_info "4. Enable: Require status checks to pass"
    print_info "5. Enable: Require branches to be up to date"
    print_info "6. Enable: Include administrators"
    
    echo
}

print_next_steps() {
    print_step "Setup complete! Next steps:"
    
    echo -e "${GREEN}✅ Repository created and configured${NC}"
    echo -e "${GREEN}✅ Code pushed to GitHub${NC}"
    echo -e "${GREEN}✅ Initial release created${NC}"
    echo
    
    print_info "Your repository is available at:"
    echo -e "${BLUE}https://github.com/$GITHUB_USERNAME/$REPO_NAME${NC}"
    echo
    
    print_info "Recommended next steps:"
    echo "1. Set up branch protection rules (if not done automatically)"
    echo "2. Configure GitHub Actions secrets if needed"
    echo "3. Enable Dependabot security updates"
    echo "4. Set up code scanning (CodeQL)"
    echo "5. Consider enabling GitHub Discussions"
    echo "6. Add a social preview image"
    echo "7. Submit to PyPI when ready"
    echo
    
    print_info "For detailed instructions, see GitHub_Setup_Instructions.md"
    echo
}

# Main execution
main() {
    print_header
    
    check_prerequisites
    get_user_input
    initialize_git
    create_github_repo
    setup_remote_and_push
    configure_repository
    create_first_release
    setup_branch_protection
    print_next_steps
    
    echo -e "${GREEN}🎉 GitHub setup completed successfully!${NC}"
}

# Run main function
main "$@"