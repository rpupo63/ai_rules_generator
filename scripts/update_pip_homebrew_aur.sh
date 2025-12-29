#!/bin/bash
# Update pip (PyPI), Homebrew, and AUR
# Usage: ./scripts/update_pip_homebrew_aur.sh [version]
# Example: ./scripts/update_pip_homebrew_aur.sh 1.0.0

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

info "Updating pip (PyPI), Homebrew, and AUR for version $VERSION"
echo

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Function to run a publish script
run_publish_script() {
    local script_name=$1
    local description=$2
    
    info "========================================="
    info "$description"
    info "========================================="
    
    if [ ! -f "$SCRIPT_DIR/$script_name" ]; then
        error "Script not found: $SCRIPT_DIR/$script_name"
    fi
    
    if bash "$SCRIPT_DIR/$script_name" "$VERSION"; then
        success "$description completed"
        echo
        return 0
    else
        error "$description failed"
    fi
}

# Run updates in sequence
run_publish_script "publish_pypi.sh" "Updating PyPI (pip installation)"
run_publish_script "publish_homebrew.sh" "Updating Homebrew"
run_publish_script "publish_aur.sh" "Updating AUR"

success "========================================="
success "All updates completed successfully!"
success "========================================="
info "Version $VERSION has been published to:"
info "  - PyPI: https://pypi.org/project/ai-rules-generator/$VERSION/"
info "  - Homebrew: tap rpupo63/homebrew-ai-rules-generator"
info "  - AUR: https://aur.archlinux.org/packages/ai-rules-generator"

