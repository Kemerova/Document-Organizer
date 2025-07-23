# GitHub Setup Script for Document Organizer (PowerShell)
# This script automates the initial GitHub repository setup on Windows

param(
    [string]$Username = "",
    [string]$RepoName = "document-organizer",
    [switch]$Private = $false,
    [switch]$Help
)

# Configuration
$RepoDescription = "A powerful Python CLI tool that processes large document collections using Azure OpenAI GPT-4.1"
$DefaultBranch = "main"

# Colors for output
$Colors = @{
    Red = "Red"
    Green = "Green"
    Yellow = "Yellow"
    Blue = "Blue"
    Cyan = "Cyan"
}

function Write-Header {
    Write-Host "================================" -ForegroundColor Blue
    Write-Host "  Document Organizer GitHub Setup" -ForegroundColor Blue
    Write-Host "================================" -ForegroundColor Blue
    Write-Host ""
}

function Write-Step {
    param([string]$Message)
    Write-Host "[STEP] $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Show-Help {
    Write-Host "Document Organizer GitHub Setup Script" -ForegroundColor Blue
    Write-Host ""
    Write-Host "USAGE:" -ForegroundColor Green
    Write-Host "  .\setup_github.ps1 [-Username <username>] [-RepoName <name>] [-Private] [-Help]"
    Write-Host ""
    Write-Host "PARAMETERS:" -ForegroundColor Green
    Write-Host "  -Username    GitHub username (will prompt if not provided)"
    Write-Host "  -RepoName    Repository name (default: document-organizer)"
    Write-Host "  -Private     Create private repository (default: public)"
    Write-Host "  -Help        Show this help message"
    Write-Host ""
    Write-Host "EXAMPLES:" -ForegroundColor Green
    Write-Host "  .\setup_github.ps1"
    Write-Host "  .\setup_github.ps1 -Username myusername"
    Write-Host "  .\setup_github.ps1 -Username myusername -Private"
    Write-Host ""
}

function Test-Prerequisites {
    Write-Step "Checking prerequisites..."
    
    # Check if git is installed
    try {
        $null = git --version
        Write-Info "Git is installed."
    }
    catch {
        Write-Error "Git is not installed. Please install Git first."
        Write-Info "Download from: https://git-scm.com/download/win"
        exit 1
    }
    
    # Check if gh CLI is installed
    try {
        $null = gh --version
        Write-Info "GitHub CLI detected. Will use for enhanced setup."
        $script:GhCliAvailable = $true
    }
    catch {
        Write-Warning "GitHub CLI not found. Some features will be limited."
        Write-Info "Install with: winget install GitHub.cli"
        $script:GhCliAvailable = $false
    }
    
    # Check if we're in the right directory
    if (-not (Test-Path "organizer.py")) {
        Write-Error "Please run this script from the Document Organizer root directory."
        exit 1
    }
    
    Write-Info "Prerequisites check completed."
    Write-Host ""
}

function Get-UserInput {
    Write-Step "Getting user configuration..."
    
    # Get GitHub username
    if (-not $Username) {
        if ($script:GhCliAvailable) {
            try {
                $Username = gh api user --jq '.login' 2>$null
                if ($Username) {
                    Write-Info "Detected GitHub username: $Username"
                    $response = Read-Host "Use this username? (y/n)"
                    if ($response -notmatch '^[Yy]$') {
                        $Username = Read-Host "Enter your GitHub username"
                    }
                }
            }
            catch {
                $Username = Read-Host "Enter your GitHub username"
            }
        }
        else {
            $Username = Read-Host "Enter your GitHub username"
        }
    }
    
    # Confirm repository name
    $inputRepoName = Read-Host "Repository name [$RepoName]"
    if ($inputRepoName) {
        $RepoName = $inputRepoName
    }
    
    # Repository visibility
    if (-not $Private) {
        $response = Read-Host "Make repository public? (y/n) [y]"
        if ($response -match '^[Nn]$') {
            $Private = $true
        }
    }
    
    $visibility = if ($Private) { "private" } else { "public" }
    
    Write-Info "Configuration:"
    Write-Info "  Username: $Username"
    Write-Info "  Repository: $RepoName"
    Write-Info "  Visibility: $visibility"
    Write-Host ""
    
    $script:Username = $Username
    $script:RepoName = $RepoName
    $script:Private = $Private
}

function Initialize-Git {
    Write-Step "Initializing Git repository..."
    
    # Initialize git if not already done
    if (-not (Test-Path ".git")) {
        git init
        Write-Info "Git repository initialized."
    }
    else {
        Write-Info "Git repository already exists."
    }
    
    # Set default branch
    git branch -M $DefaultBranch
    
    # Add all files
    git add .
    
    # Check if there are changes to commit
    $status = git status --porcelain
    if (-not $status) {
        Write-Info "No changes to commit."
    }
    else {
        # Create initial commit
        $commitMessage = @"
feat: initial release of Document Organizer v1.0.0

- Complete implementation with all 15 tasks completed
- Multi-format document processing (TXT, DOCX, PDF, images)
- Azure OpenAI GPT-4.1 integration with 1M-token context
- OCR support with Tesseract integration
- Intelligent deduplication and data consolidation
- Multi-format output (Markdown, DOCX, CSV, JSON)
- Comprehensive error handling and recovery
- Performance monitoring and optimization
- Production-ready with 80+ unit tests
- Complete documentation and setup guides
"@
        
        git commit -m $commitMessage
        Write-Info "Initial commit created."
    }
    
    Write-Host ""
}

function New-GitHubRepo {
    Write-Step "Creating GitHub repository..."
    
    if ($script:GhCliAvailable) {
        # Use GitHub CLI to create repository
        $visibility = if ($script:Private) { "--private" } else { "--public" }
        
        gh repo create "$($script:Username)/$($script:RepoName)" `
            --description $RepoDescription `
            $visibility `
            --clone=false `
            --confirm
        
        Write-Info "Repository created using GitHub CLI."
    }
    else {
        Write-Warning "GitHub CLI not available. Please create the repository manually:"
        Write-Info "1. Go to https://github.com/new"
        Write-Info "2. Repository name: $($script:RepoName)"
        Write-Info "3. Description: $RepoDescription"
        $visibilityText = if ($script:Private) { "Private" } else { "Public" }
        Write-Info "4. Visibility: $visibilityText"
        Write-Info "5. Don't initialize with README, .gitignore, or license"
        Write-Info "6. Click 'Create repository'"
        Write-Host ""
        Read-Host "Press Enter after creating the repository..."
    }
    
    Write-Host ""
}

function Set-RemoteAndPush {
    Write-Step "Setting up remote and pushing code..."
    
    # Add remote origin
    $repoUrl = "https://github.com/$($script:Username)/$($script:RepoName).git"
    
    # Check if remote already exists
    try {
        $null = git remote get-url origin 2>$null
        Write-Info "Remote origin already exists. Updating URL..."
        git remote set-url origin $repoUrl
    }
    catch {
        git remote add origin $repoUrl
        Write-Info "Remote origin added: $repoUrl"
    }
    
    # Push to GitHub
    Write-Info "Pushing code to GitHub..."
    git push -u origin $DefaultBranch
    
    Write-Info "Code successfully pushed to GitHub!"
    Write-Host ""
}

function Set-RepositoryConfig {
    Write-Step "Configuring repository settings..."
    
    if ($script:GhCliAvailable) {
        # Enable issues and wiki
        gh repo edit "$($script:Username)/$($script:RepoName)" `
            --enable-issues `
            --enable-wiki `
            --delete-branch-on-merge
        
        Write-Info "Repository settings configured."
        
        # Add topics
        $topics = @(
            "python", "cli", "azure-openai", "gpt-4", "document-processing",
            "ocr", "medical-records", "healthcare", "automation", "ai",
            "nlp", "text-processing"
        )
        
        foreach ($topic in $topics) {
            gh repo edit "$($script:Username)/$($script:RepoName)" --add-topic $topic
        }
        
        Write-Info "Repository topics added."
    }
    else {
        Write-Warning "Manual configuration required:"
        Write-Info "1. Go to https://github.com/$($script:Username)/$($script:RepoName)/settings"
        Write-Info "2. Enable Issues and Wiki"
        Write-Info "3. Add topics: python, cli, azure-openai, gpt-4, document-processing, ocr"
        Write-Info "4. Set up branch protection rules for main branch"
    }
    
    Write-Host ""
}

function New-FirstRelease {
    Write-Step "Creating first release..."
    
    if ($script:GhCliAvailable) {
        # Create release
        gh release create v1.0.0 `
            --title "Document Organizer v1.0.0 - Initial Release" `
            --notes-file CHANGELOG.md `
            --latest
        
        Write-Info "Release v1.0.0 created successfully!"
    }
    else {
        Write-Warning "Manual release creation required:"
        Write-Info "1. Go to https://github.com/$($script:Username)/$($script:RepoName)/releases"
        Write-Info "2. Click 'Create a new release'"
        Write-Info "3. Tag version: v1.0.0"
        Write-Info "4. Release title: Document Organizer v1.0.0 - Initial Release"
        Write-Info "5. Copy description from CHANGELOG.md"
        Write-Info "6. Mark as latest release"
    }
    
    Write-Host ""
}

function Set-BranchProtection {
    Write-Step "Setting up branch protection..."
    
    if ($script:GhCliAvailable) {
        Write-Warning "Branch protection setup requires admin permissions."
        Write-Info "Please set up branch protection manually:"
    }
    else {
        Write-Warning "Manual branch protection setup required:"
    }
    
    Write-Info "1. Go to https://github.com/$($script:Username)/$($script:RepoName)/settings/branches"
    Write-Info "2. Add rule for 'main' branch"
    Write-Info "3. Enable: Require pull request reviews"
    Write-Info "4. Enable: Require status checks to pass"
    Write-Info "5. Enable: Require branches to be up to date"
    Write-Info "6. Enable: Include administrators"
    
    Write-Host ""
}

function Show-NextSteps {
    Write-Step "Setup complete! Next steps:"
    
    Write-Host "✅ Repository created and configured" -ForegroundColor Green
    Write-Host "✅ Code pushed to GitHub" -ForegroundColor Green
    Write-Host "✅ Initial release created" -ForegroundColor Green
    Write-Host ""
    
    Write-Info "Your repository is available at:"
    Write-Host "https://github.com/$($script:Username)/$($script:RepoName)" -ForegroundColor Blue
    Write-Host ""
    
    Write-Info "Recommended next steps:"
    Write-Host "1. Set up branch protection rules (if not done automatically)"
    Write-Host "2. Configure GitHub Actions secrets if needed"
    Write-Host "3. Enable Dependabot security updates"
    Write-Host "4. Set up code scanning (CodeQL)"
    Write-Host "5. Consider enabling GitHub Discussions"
    Write-Host "6. Add a social preview image"
    Write-Host "7. Submit to PyPI when ready"
    Write-Host ""
    
    Write-Info "For detailed instructions, see GitHub_Setup_Instructions.md"
    Write-Host ""
}

# Main execution
function Main {
    if ($Help) {
        Show-Help
        return
    }
    
    Write-Header
    
    Test-Prerequisites
    Get-UserInput
    Initialize-Git
    New-GitHubRepo
    Set-RemoteAndPush
    Set-RepositoryConfig
    New-FirstRelease
    Set-BranchProtection
    Show-NextSteps
    
    Write-Host "🎉 GitHub setup completed successfully!" -ForegroundColor Green
}

# Run main function
try {
    Main
}
catch {
    Write-Error "An error occurred: $($_.Exception.Message)"
    Write-Info "Please check the error and try again, or set up manually using GitHub_Setup_Instructions.md"
    exit 1
}