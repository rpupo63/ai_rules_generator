#!/bin/bash
# Prepare WinGet manifests for publishing
# Usage: ./scripts/publish_winget.sh [version]
# Example: ./scripts/publish_winget.sh 1.0.0
#
# Note: WinGet publishing requires a PR to microsoft/winget-pkgs
# This script validates manifests and provides instructions

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check if running from repo root
if [ ! -f "ai_rules_generator/__init__.py" ]; then
    error "Must be run from repository root"
fi

# Get version
VERSION=${1:-$(grep -oP '__version__ = "\K[^"]+' ai_rules_generator/__init__.py)}
REPO="rpupo63/ai-rules-generator"
RELEASE_TAG="v$VERSION"

info "Preparing WinGet manifests for version $VERSION"

# Check for .winget directory
WINGET_DIR=".winget/manifests"
if [ ! -d "$WINGET_DIR" ]; then
    warning "WinGet manifests directory not found: $WINGET_DIR"
    info "WinGet support is optional and may not be set up yet"
    info "See PUBLISHING.md section 4 for setup instructions"
    exit 0
fi

# Find manifest directory (format: a/AIRulesGenerator/AIRulesGenerator/VERSION/)
MANIFEST_DIR=$(find "$WINGET_DIR" -type d -name "$VERSION" 2>/dev/null | head -1)

if [ -z "$MANIFEST_DIR" ]; then
    warning "No manifest directory found for version $VERSION"
    info "WinGet manifest structure should be:"
    info "  .winget/manifests/a/AIRulesGenerator/AIRulesGenerator/$VERSION/"
    info ""
    info "You may need to create or rename the version directory"
    read -p "Continue with validation anyway? [y/N]: " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || exit 0
else
    success "Found manifest directory: $MANIFEST_DIR"
fi

# Validate manifests (if winget is available)
if command -v winget &> /dev/null; then
    info "Validating WinGet manifests..."
    
    if [ -n "$MANIFEST_DIR" ]; then
        if winget validate --manifest "$MANIFEST_DIR" 2>&1; then
            success "Manifests are valid"
        else
            warning "Manifest validation failed. Check for errors above."
        fi
    else
        warning "Cannot validate without manifest directory"
    fi
else
    warning "winget command not found (Windows-only tool)"
    info "On Windows, validate with:"
    info "  winget validate --manifest .winget/manifests/a/AIRulesGenerator/AIRulesGenerator/$VERSION/"
fi

# Check for placeholder checksums
if [ -n "$MANIFEST_DIR" ]; then
    info "Checking for placeholder checksums..."
    if grep -r "REPLACE_WITH\|PLACEHOLDER\|TODO" "$MANIFEST_DIR" 2>/dev/null; then
        warning "Found placeholder values in manifests"
        info "Update SHA256 hashes in installer manifests:"
        info "  Download Windows executables from GitHub release, then calculate hashes:"
        info "  For x64: sha256sum ai-rules-generator-${VERSION}-win64.exe"
        info "  For x86: sha256sum ai-rules-generator-${VERSION}-win32.exe"
        info "  Update the InstallerSha256 fields in the installer manifest YAML file"
    else
        success "No placeholders found"
    fi
fi

# Instructions for publishing
echo ""
success "WinGet manifests ready"
echo ""
info "To publish to WinGet:"
info "  1. Fork https://github.com/microsoft/winget-pkgs"
info "  2. Clone your fork"
info "  3. Copy manifest directory:"
if [ -n "$MANIFEST_DIR" ]; then
    info "     cp -r $MANIFEST_DIR ../winget-pkgs/manifests/a/AIRulesGenerator/AIRulesGenerator/"
else
    info "     cp -r .winget/manifests/a/AIRulesGenerator/AIRulesGenerator/$VERSION/ ../winget-pkgs/manifests/a/AIRulesGenerator/AIRulesGenerator/"
fi
info "  4. Commit and create PR:"
info "     cd ../winget-pkgs"
info "     git add manifests/a/AIRulesGenerator/AIRulesGenerator/$VERSION/"
info "     git commit -m 'Add AIRulesGenerator.AIRulesGenerator version $VERSION'"
info "     git push origin main"
info "     # Create PR on GitHub"
info ""
info "After PR is merged, users can install with:"
info "  winget install AIRulesGenerator.AIRulesGenerator"


