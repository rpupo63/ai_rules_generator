#!/bin/bash
# Publish to PyPI
# Usage: ./scripts/publish_pypi.sh [version]
# Example: ./scripts/publish_pypi.sh 1.0.0

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

info "Publishing to PyPI for version $VERSION"

# Check if twine is installed
if ! command -v twine &> /dev/null; then
    error "twine is required. Install with: pip install twine"
fi

# Check if packages are built
if [ ! -d "dist" ] || [ -z "$(ls -A dist/*.whl dist/*.tar.gz 2>/dev/null)" ]; then
    info "Building packages..."
    if ! command -v python &> /dev/null && ! command -v python3 &> /dev/null; then
        error "Python is required to build packages"
    fi
    
    PYTHON_CMD=$(command -v python3 || command -v python)
    $PYTHON_CMD -m pip install -q build
    $PYTHON_CMD -m build
fi

# Verify packages exist
if [ ! -f "dist/ai_rules_generator-${VERSION}-py3-none-any.whl" ] || \
   [ ! -f "dist/ai_rules_generator-${VERSION}.tar.gz" ]; then
    warning "Expected packages not found for version $VERSION"
    info "Found packages:"
    ls -la dist/
    read -p "Continue anyway? [y/N]: " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]] || error "Aborted"
fi

# Check PyPI credentials
if [ ! -f "$HOME/.pypirc" ]; then
    warning "No ~/.pypirc found. You'll need to enter credentials."
    info "Alternatively, create ~/.pypirc with:"
    echo "[distutils]"
    echo "index-servers = pypi"
    echo ""
    echo "[pypi]"
    echo "username = __token__"
    echo "password = pypi-YOUR_TOKEN_HERE"
fi

# Upload to PyPI
info "Uploading to PyPI..."
if twine upload dist/ai_rules_generator-${VERSION}*; then
    success "Published to PyPI: https://pypi.org/project/ai-rules-generator/$VERSION/"
    info "Verify installation: pip install ai-rules-generator==$VERSION"
else
    error "Failed to upload to PyPI"
fi


