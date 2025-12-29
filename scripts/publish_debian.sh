#!/bin/bash
# Build and publish Debian package
# Usage: ./scripts/publish_debian.sh [version]
# Example: ./scripts/publish_debian.sh 1.0.0
#
# This script builds a .deb package and optionally:
# 1. Uploads to GitHub releases
# 2. Provides instructions for PPA upload

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
RELEASE_TAG="v$VERSION"

info "Building Debian package for version $VERSION"

# Check if we're on Debian/Ubuntu
if [ ! -f "/etc/debian_version" ] && ! grep -q "Ubuntu" /etc/os-release 2>/dev/null; then
    warning "Not on Debian/Ubuntu. Some commands may not work."
fi

# Check for build tools
if ! command -v dpkg-buildpackage &> /dev/null; then
    warning "dpkg-buildpackage not found"
    info "Install with: sudo apt install debhelper dh-python python3-all python3-setuptools devscripts"
    read -p "Continue anyway? [y/N]: " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || error "Aborted"
fi

# Check debian/changelog
if [ ! -f "debian/changelog" ]; then
    error "debian/changelog not found"
fi

# Check if changelog has current version
if ! grep -q "^ai-rules-generator (${VERSION}" debian/changelog; then
    warning "debian/changelog doesn't have entry for version $VERSION"
    info "Update with: dch -v ${VERSION}-1 'Release version $VERSION'"
    read -p "Continue anyway? [y/N]: " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || error "Aborted"
fi

# Clean previous builds
info "Cleaning previous builds..."
rm -f ../ai-rules-generator_*.deb ../ai-rules-generator_*.changes ../ai-rules-generator_*.dsc ../ai-rules-generator_*.tar.gz 2>/dev/null || true

# Build package
info "Building Debian package..."
if dpkg-buildpackage -us -uc -b 2>&1 | tee /tmp/dpkg-build.log; then
    success "Package built successfully"
else
    error "Package build failed. Check /tmp/dpkg-build.log"
fi

# Find the .deb file
DEB_FILE=$(ls ../ai-rules-generator_*.deb 2>/dev/null | head -1)
if [ -z "$DEB_FILE" ]; then
    error "Could not find built .deb file"
fi

success "Package built: $DEB_FILE"

# Ask about uploading to GitHub
if command -v gh &> /dev/null; then
    read -p "Upload to GitHub release? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Uploading to GitHub release $RELEASE_TAG..."
        if gh release upload "$RELEASE_TAG" "$DEB_FILE"; then
            success "Uploaded to GitHub release"
        else
            warning "Upload failed. Release may not exist. Create it first:"
            info "  gh release create $RELEASE_TAG"
        fi
    fi
else
    warning "GitHub CLI (gh) not found. Install with:"
    info "  sudo apt install gh  # Debian/Ubuntu"
    info "  brew install gh      # macOS"
fi

# PPA instructions
echo ""
info "For PPA upload (Launchpad):"
info "  1. Build source package: debuild -S -sa"
info "  2. Upload: dput ppa:rpupo63/ai-rules-generator ../ai-rules-generator_${VERSION}-1_source.changes"
info "  3. Or use direct .deb: Users can install with:"
info "     wget https://github.com/rpupo63/ai-rules-generator/releases/download/${RELEASE_TAG}/$(basename $DEB_FILE)"
info "     sudo apt install ./$(basename $DEB_FILE)"


