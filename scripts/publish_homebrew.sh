#!/bin/bash
# Publish to Homebrew tap
# Usage: ./scripts/publish_homebrew.sh [version]
# Example: ./scripts/publish_homebrew.sh 1.0.0
#
# Prerequisites:
# - Tap repository: rpupo63/homebrew-ai-rules-generator
# - Formula file: Formula/ai-rules-generator.rb

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
TAP_REPO="rpupo63/homebrew-ai-rules-generator"

info "Publishing to Homebrew tap for version $VERSION"

# Check if formula exists
if [ ! -f "Formula/ai-rules-generator.rb" ]; then
    error "Formula file not found: Formula/ai-rules-generator.rb"
fi

# Check if tap directory exists
TAP_DIR="$HOME/.package-manager-repos/homebrew-ai-rules-generator"
if [ ! -d "$TAP_DIR" ]; then
    warning "Tap repository not found at $TAP_DIR"
    info "Setting up tap repository..."
    
    mkdir -p "$(dirname "$TAP_DIR")"
    
    if git clone "https://github.com/$TAP_REPO.git" "$TAP_DIR" 2>/dev/null; then
        success "Cloned tap repository"
    else
        warning "Could not clone tap repository. You may need to create it first:"
        info "  1. Create repo on GitHub: $TAP_REPO"
        info "  2. Or clone manually: git clone https://github.com/$TAP_REPO.git $TAP_DIR"
        read -p "Continue with manual setup? [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "Aborted"
        fi
        
        mkdir -p "$TAP_DIR"
        cd "$TAP_DIR"
        git init
        git remote add origin "https://github.com/$TAP_REPO.git" 2>/dev/null || true
        cd - > /dev/null
    fi
fi

# Copy formula to tap
info "Updating formula in tap..."
cp Formula/ai-rules-generator.rb "$TAP_DIR/ai-rules-generator.rb"

cd "$TAP_DIR"

# Check if formula has placeholder checksum
if grep -q "REPLACE_WITH_ACTUAL_SHA256" ai-rules-generator.rb; then
    warning "Formula contains placeholder checksum. Updating..."
    
    # Download release tarball and calculate checksum
    TARBALL_URL="https://github.com/$REPO/archive/v${VERSION}.tar.gz"
    TMP_TARBALL="/tmp/ai-rules-generator-${VERSION}.tar.gz"
    
    info "Downloading release tarball..."
    curl -L -o "$TMP_TARBALL" "$TARBALL_URL" || error "Failed to download tarball"
    
    # Calculate checksum
    if command -v shasum &> /dev/null; then
        CHECKSUM=$(shasum -a 256 "$TMP_TARBALL" | awk '{print $1}')
    elif command -v sha256sum &> /dev/null; then
        CHECKSUM=$(sha256sum "$TMP_TARBALL" | awk '{print $1}')
    else
        error "No checksum tool found (need shasum or sha256sum)"
    fi
    
    # Update checksum in formula
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s/sha256 \"REPLACE_WITH_ACTUAL_SHA256\"/sha256 \"$CHECKSUM\"/" ai-rules-generator.rb
    else
        sed -i "s/sha256 \"REPLACE_WITH_ACTUAL_SHA256\"/sha256 \"$CHECKSUM\"/" ai-rules-generator.rb
    fi
    
    success "Updated checksum: $CHECKSUM"
    rm -f "$TMP_TARBALL"
fi

# Commit and push
if [ -n "$(git status --porcelain)" ]; then
    git add ai-rules-generator.rb
    git commit -m "Update ai-rules-generator to $VERSION"
    
    if git push origin main; then
        success "Published to Homebrew tap"
        info "Users can install with:"
        info "  brew tap $TAP_REPO"
        info "  brew install ai-rules-generator"
    else
        error "Failed to push to tap repository"
    fi
else
    info "No changes to commit"
fi

cd - > /dev/null


