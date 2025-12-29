#!/bin/bash
# Prepare Flatpak for publishing
# Usage: ./scripts/publish_flatpak.sh [version]
# Example: ./scripts/publish_flatpak.sh 1.0.0
#
# Note: Flatpak publishing requires a manual PR to Flathub
# This script prepares the files and provides instructions

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

info "Preparing Flatpak for version $VERSION"

# Check flatpak directory
if [ ! -d "flatpak" ]; then
    error "flatpak directory not found"
fi

if [ ! -f "flatpak/com.github.ai_rules_generator.AIRulesGenerator.yaml" ]; then
    error "Flatpak manifest not found"
fi

# Check if checksums need updating
info "Checking Flatpak manifest..."
if grep -q "REPLACE_WITH" flatpak/com.github.ai_rules_generator.AIRulesGenerator.yaml; then
    warning "Flatpak manifest contains placeholder checksums"
    
    # Calculate checksums
    TARBALL_URL="https://github.com/$REPO/archive/${RELEASE_TAG}.tar.gz"
    TMP_TARBALL="/tmp/ai-rules-generator-${VERSION}.tar.gz"
    
    info "Downloading release tarball for checksum..."
    curl -L -o "$TMP_TARBALL" "$TARBALL_URL" || error "Failed to download tarball"
    
    if command -v shasum &> /dev/null; then
        CHECKSUM=$(shasum -a 256 "$TMP_TARBALL" | awk '{print $1}')
    elif command -v sha256sum &> /dev/null; then
        CHECKSUM=$(sha256sum "$TMP_TARBALL" | awk '{print $1}')
    else
        error "No checksum tool found"
    fi
    
    info "Source checksum: $CHECKSUM"
    info "Update this in flatpak/com.github.ai_rules_generator.AIRulesGenerator.yaml"
    
    rm -f "$TMP_TARBALL"
fi

# Build Flatpak (optional, for testing)
if command -v flatpak-builder &> /dev/null; then
    read -p "Build Flatpak package for testing? [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        info "Building Flatpak package..."
        cd flatpak
        
        # Clean previous build
        rm -rf build-dir repo 2>/dev/null || true
        
        # Build
        if flatpak-builder --force-clean build-dir com.github.ai_rules_generator.AIRulesGenerator.yaml; then
            success "Flatpak package built successfully"
            info "Test with: flatpak-builder --run build-dir com.github.ai_rules_generator.AIRulesGenerator.yaml ai-rules-generator --help"
        else
            warning "Flatpak build failed. Check manifest for errors."
        fi
        
        cd - > /dev/null
    fi
else
    warning "flatpak-builder not found. Install with:"
    info "  sudo apt install flatpak flatpak-builder  # Debian/Ubuntu"
    info "  sudo pacman -S flatpak flatpak-builder    # Arch"
fi

# Instructions for Flathub submission
echo ""
success "Flatpak files ready in flatpak/ directory"
echo ""
info "To publish to Flathub:"
info "  1. Fork https://github.com/flathub/flathub"
info "  2. Clone your fork"
info "  3. Create directory: com.github.ai_rules_generator.AIRulesGenerator"
info "  4. Copy files from flatpak/ directory:"
info "     - com.github.ai_rules_generator.AIRulesGenerator.yaml"
info "     - com.github.ai_rules_generator.AIRulesGenerator.desktop"
info "     - com.github.ai_rules_generator.AIRulesGenerator.metainfo.xml"
info "     - com.github.ai_rules_generator.AIRulesGenerator.svg"
info "  5. Update app ID if needed (change ai_rules_generator to rpupo63 in app ID)"
info "  6. Commit and create PR:"
info "     git add ."
info "     git commit -m 'Add com.github.ai_rules_generator.AIRulesGenerator'"
info "     git push origin main"
info "     # Create PR on GitHub"
info ""
info "After PR is merged, users can install with:"
info "  flatpak install flathub com.github.ai_rules_generator.AIRulesGenerator"


