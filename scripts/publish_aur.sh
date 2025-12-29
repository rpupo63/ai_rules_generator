#!/bin/bash
# Publish to AUR (Arch User Repository)
# Usage: ./scripts/publish_aur.sh [version]
# Example: ./scripts/publish_aur.sh 1.0.0
#
# Prerequisites:
# - AUR account: https://aur.archlinux.org/register
# - SSH key configured: ssh -T aur@aur.archlinux.org
# - PKGBUILD file in repo root

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

info "Publishing to AUR for version $VERSION"

# Check if PKGBUILD exists
if [ ! -f "PKGBUILD" ]; then
    error "PKGBUILD file not found"
fi

# Check SSH access to AUR
info "Checking AUR SSH access..."
if ! ssh -T aur@aur.archlinux.org 2>&1 | grep -q "successfully authenticated"; then
    warning "AUR SSH access not configured"
    info "Set up SSH key at: https://aur.archlinux.org/account/"
    info "Test with: ssh -T aur@aur.archlinux.org"
    read -p "Continue anyway? [y/N]: " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || error "Aborted"
fi

# Check if makepkg is available (for generating .SRCINFO)
if ! command -v makepkg &> /dev/null; then
    warning "makepkg not found. Will generate .SRCINFO manually if needed."
fi

# Clone or use existing AUR repo
AUR_DIR="/tmp/aur-ai-rules-generator"
if [ -d "$AUR_DIR" ]; then
    info "Cleaning up existing AUR directory..."
    rm -rf "$AUR_DIR"
fi

info "Cloning AUR repository..."
if git clone ssh://aur@aur.archlinux.org/ai-rules-generator.git "$AUR_DIR" 2>/dev/null; then
    success "Cloned AUR repository"
else
    error "Failed to clone AUR repository. Check SSH access: ssh -T aur@aur.archlinux.org"
fi

# Copy PKGBUILD
info "Copying PKGBUILD..."
cp PKGBUILD "$AUR_DIR/"

# Generate .SRCINFO
cd "$AUR_DIR"
if command -v makepkg &> /dev/null; then
    info "Generating .SRCINFO..."
    makepkg --printsrcinfo > .SRCINFO
    success "Generated .SRCINFO"
else
    warning "makepkg not available, skipping .SRCINFO generation"
    info "You'll need to generate it manually: makepkg --printsrcinfo > .SRCINFO"
fi

# Commit and push
if [ -n "$(git status --porcelain)" ]; then
    git add PKGBUILD .SRCINFO 2>/dev/null || git add PKGBUILD
    git commit -m "Update to version $VERSION"
    
    if git push origin master; then
        success "Published to AUR: https://aur.archlinux.org/packages/ai-rules-generator"
        info "Users can install with: yay -S ai-rules-generator"
    else
        error "Failed to push to AUR"
    fi
else
    info "No changes to commit"
fi

cd - > /dev/null
rm -rf "$AUR_DIR"


