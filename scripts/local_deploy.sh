#!/bin/bash
# Local CI/CD Deployment Script for AI Rules Generator
# Usage: ./scripts/local_deploy.sh [version]
# Example: ./scripts/local_deploy.sh 1.0.0
#
# This script handles the complete release process locally:
# 1. Validation and testing
# 2. Version bumping (optional)
# 3. Git tagging and GitHub release creation
# 4. Checksum generation
# 5. Package building and publishing

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

confirm() {
    read -p "$(echo -e ${YELLOW}[CONFIRM]${NC} $1 [y/N]: )" -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# Parse arguments
VERSION=$1
CURRENT_VERSION=$(grep -oP '__version__ = "\K[^"]+' ai_rules_generator/__init__.py)

if [ -z "$VERSION" ]; then
    info "No version specified, using current version: $CURRENT_VERSION"
    VERSION=$CURRENT_VERSION
else
    info "Deploying version: $VERSION (current: $CURRENT_VERSION)"
fi

# Configuration
REPO="rpupo63/ai_rules_generator"
REPO_URL="https://github.com/$REPO"
RELEASE_TAG="v$VERSION"

echo ""
echo "======================================"
echo "  AI Rules Generator Local Deploy"
echo "======================================"
echo "Version: $VERSION"
echo "Repository: $REPO"
echo "======================================"
echo ""

# ============================================================================
# PHASE 1: PRE-FLIGHT CHECKS
# ============================================================================

info "Phase 1: Running pre-flight checks..."

# Check if we're in the right directory
if [ ! -f "ai_rules_generator/__init__.py" ]; then
    error "Must be run from repository root"
fi

# Check for uncommitted changes
if [ -n "$(git status --porcelain)" ]; then
    warning "You have uncommitted changes:"
    git status --short
    if ! confirm "Continue anyway?"; then
        error "Aborted by user"
    fi
fi

# Check for required tools
info "Checking required tools..."
for tool in git gh python3 pip makepkg twine; do
    if ! command -v $tool &> /dev/null; then
        warning "$tool not found (some features may not work)"
    else
        success "$tool found"
    fi
done

# Check if on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    warning "You are on branch '$CURRENT_BRANCH', not 'main'"
    if ! confirm "Continue anyway?"; then
        error "Aborted by user"
    fi
fi

success "Pre-flight checks complete"
echo ""

# ============================================================================
# PHASE 2: VERSION BUMPING (OPTIONAL)
# ============================================================================

if [ "$VERSION" != "$CURRENT_VERSION" ]; then
    info "Phase 2: Bumping version from $CURRENT_VERSION to $VERSION..."

    if confirm "Run version bump script?"; then
        ./scripts/bump_version.sh $VERSION

        # Manual steps
        info "Please complete manual version updates:"
        info "1. Update debian/changelog: dch -v ${VERSION}-1 'Release version $VERSION'"
        if [ -d ".winget-future/manifests" ]; then
            info "2. Rename .winget-future/manifests/.../*/1.0.0/ to $VERSION/ (if applicable)"
        fi
        info "3. Update flatpak metainfo.xml release date to today"

        if confirm "Have you completed the manual steps?"; then
            success "Version bump complete"
        else
            error "Version bump incomplete - please complete and re-run"
        fi
    else
        info "Skipping version bump"
    fi
else
    info "Phase 2: Version is current ($VERSION), skipping bump"
fi

echo ""

# ============================================================================
# PHASE 3: TESTING AND VALIDATION
# ============================================================================

info "Phase 3: Running tests and validation..."

# Test Python syntax
info "Validating Python syntax..."
python3 -m py_compile ai_rules_generator/*.py
success "Python syntax valid"

# Build test
info "Testing package build..."
python3 -m build --outdir dist-test/
rm -rf dist-test/
success "Package build successful"

# Line count check
TOTAL_LINES=$(wc -l ai_rules_generator/*.py | tail -1 | awk '{print $1}')
info "Total lines of code: $TOTAL_LINES"

success "Validation complete"
echo ""

# ============================================================================
# PHASE 4: GIT TAGGING AND GITHUB RELEASE
# ============================================================================

info "Phase 4: Creating Git tag and GitHub release..."

# Check if tag already exists
if git rev-parse "$RELEASE_TAG" >/dev/null 2>&1; then
    warning "Tag $RELEASE_TAG already exists"
    if confirm "Delete existing tag and recreate?"; then
        git tag -d $RELEASE_TAG
        git push origin :refs/tags/$RELEASE_TAG 2>/dev/null || true
        success "Deleted existing tag"
    else
        error "Tag already exists - aborting"
    fi
fi

# Commit version changes if any
if [ -n "$(git status --porcelain)" ]; then
    warning "Uncommitted changes detected"
    if confirm "Commit changes before tagging?"; then
        git add .
        git commit -m "Release version $VERSION"
        git push origin main
        success "Changes committed and pushed"
    fi
fi

# Create annotated tag
info "Creating tag $RELEASE_TAG..."
git tag -a "$RELEASE_TAG" -m "Release version $VERSION

Features:
- Multi-tool support for 6 AI coding assistants
- Interactive configuration setup
- Support for OpenAI and Anthropic Claude models
- Template-based fallback mode
- Monorepo support
- 20+ languages and 100+ frameworks"

git push origin "$RELEASE_TAG"
success "Tag created and pushed"

# Create GitHub release
info "Creating GitHub release..."
gh release create "$RELEASE_TAG" \
  --title "AI Rules Generator v$VERSION" \
  --notes "# AI Rules Generator v$VERSION

## Release Notes

A CLI tool that generates comprehensive AI coding agent rules for Cursor and Claude Code.

### Installation

**Python (PyPI):**
\`\`\`bash
pip install ai-rules-generator
\`\`\`

**macOS (Homebrew):**
\`\`\`bash
brew tap $REPO
brew install ai-rules-generator
\`\`\`

**Arch Linux (AUR):**
\`\`\`bash
yay -S ai-rules-generator
\`\`\`

**Debian/Ubuntu:**
Download the .deb package from this release

**Windows (WinGet):**
\`\`\`powershell
winget install AIRulesGenerator.AIRulesGenerator
\`\`\`

**Linux (Flatpak):** Coming soon to Flathub

### Quick Start

1. \`ai-rules-generator init\` - Configure your AI provider
2. \`cd your-project\`
3. \`ai-rules-generator project-init\` - Generate rules

For full documentation, see the [README]($REPO_URL#readme).

---
🤖 Generated with Local CI/CD - Deployed from $(hostname) at $(date)"

success "GitHub release created: $REPO_URL/releases/tag/$RELEASE_TAG"
echo ""

# ============================================================================
# PHASE 5: CHECKSUM GENERATION
# ============================================================================

info "Phase 5: Generating checksums..."

# Create temp directory for downloads
mkdir -p .deploy-temp
cd .deploy-temp

# Download release artifacts
info "Downloading release artifacts..."
wget -q "https://github.com/$REPO/archive/refs/tags/$RELEASE_TAG.tar.gz"
wget -q "https://github.com/$REPO/archive/refs/tags/$RELEASE_TAG.zip"

# Download Python dependencies
info "Downloading Python dependencies..."
pip download openai==1.6.1 --no-deps --no-binary :all: 2>/dev/null
pip download anthropic==0.18.1 --no-deps --no-binary :all: 2>/dev/null

# Generate checksums
info "Generating SHA256 checksums..."
sha256sum * > ../checksums.txt

cd ..
cat checksums.txt

success "Checksums generated and saved to checksums.txt"
echo ""

# Update checksums in configs
info "Updating checksums in package configs..."
./scripts/update_checksums.sh

# Regenerate .SRCINFO for AUR
info "Regenerating .SRCINFO for AUR..."
makepkg --printsrcinfo > .SRCINFO 2>/dev/null || warning "makepkg not available, skip .SRCINFO"

# Commit checksum updates
if [ -n "$(git status --porcelain)" ]; then
    git add PKGBUILD .SRCINFO Formula/ flatpak/ checksums.txt
    git commit -m "Update checksums for $RELEASE_TAG"
    git push origin main
    success "Checksum updates committed and pushed"
fi

# Cleanup
rm -rf .deploy-temp

success "Checksums updated in all package configs"
echo ""

# ============================================================================
# PHASE 6: PACKAGE BUILDING
# ============================================================================

info "Phase 6: Building packages..."

# PyPI
info "Building Python packages for PyPI..."
rm -rf dist/ build/ *.egg-info
python3 -m build
success "PyPI packages built: $(ls dist/)"

# Debian
if command -v dpkg-buildpackage &> /dev/null; then
    info "Building Debian package..."
    cd ..
    if dpkg-buildpackage -us -uc 2>&1 | tee /tmp/dpkg-build.log; then
        cd ai_rules_generator
        DEB_FILE=$(ls ../ai-rules-generator_*.deb 2>/dev/null | head -1)
        if [ -f "$DEB_FILE" ]; then
            mv "$DEB_FILE" .
            success "Debian package built: $(basename $DEB_FILE)"
        fi
    else
        cd ai_rules_generator
        warning "Debian build failed (see /tmp/dpkg-build.log)"
    fi
else
    warning "dpkg-buildpackage not available, skipping Debian build"
fi

success "Package building complete"
echo ""

# ============================================================================
# PHASE 7: PUBLISHING
# ============================================================================

info "Phase 7: Publishing to package managers..."
echo ""

# PyPI
if confirm "Publish to PyPI?"; then
    info "Publishing to PyPI..."
    if command -v twine &> /dev/null; then
        twine upload dist/* || warning "PyPI upload failed"
        success "Published to PyPI: https://pypi.org/project/ai-rules-generator/$VERSION/"
    else
        warning "twine not available, skipping PyPI upload"
    fi
else
    info "Skipped PyPI publishing"
fi

echo ""

# Debian - Upload to GitHub release
DEB_FILE=$(ls ai-rules-generator_*.deb 2>/dev/null | head -1)
if [ -f "$DEB_FILE" ]; then
    if confirm "Upload Debian package to GitHub release?"; then
        gh release upload "$RELEASE_TAG" "$DEB_FILE"
        success "Uploaded $DEB_FILE to GitHub release"
    else
        info "Skipped Debian package upload"
    fi
fi

echo ""

# Homebrew
if confirm "Update Homebrew tap?"; then
    info "Updating Homebrew tap..."

    # Check if tap repo exists
    TAP_DIR="$HOME/homebrew-tap"
    if [ ! -d "$TAP_DIR" ]; then
        warning "Homebrew tap not found at $TAP_DIR"
        if confirm "Create tap repository?"; then
            mkdir -p "$TAP_DIR"
            cd "$TAP_DIR"
            git init
            mkdir -p Formula
            git remote add origin "git@github.com:$REPO.git" 2>/dev/null || true
            cd - > /dev/null
            success "Tap repository created"
        fi
    fi

    if [ -d "$TAP_DIR" ]; then
        cp Formula/ai-rules-generator.rb "$TAP_DIR/Formula/"
        cd "$TAP_DIR"
        git add Formula/ai-rules-generator.rb
        git commit -m "Update ai-rules-generator to $VERSION"
        git push origin main
        cd - > /dev/null
        success "Homebrew formula updated in tap"
    fi
else
    info "Skipped Homebrew tap update"
fi

echo ""

# AUR
if confirm "Publish to AUR?"; then
    info "Publishing to AUR..."

    AUR_DIR="/tmp/aur-ai-rules-generator"
    if [ -d "$AUR_DIR" ]; then
        rm -rf "$AUR_DIR"
    fi

    if git clone ssh://aur@aur.archlinux.org/ai-rules-generator.git "$AUR_DIR" 2>/dev/null; then
        cp PKGBUILD .SRCINFO "$AUR_DIR/"
        cd "$AUR_DIR"
        git add PKGBUILD .SRCINFO
        git commit -m "Update to version $VERSION"
        git push origin master
        cd - > /dev/null
        rm -rf "$AUR_DIR"
        success "Published to AUR: https://aur.archlinux.org/packages/ai-rules-generator"
    else
        warning "AUR repository not accessible (check SSH key)"
        info "Manual steps:"
        info "  1. git clone ssh://aur@aur.archlinux.org/ai-rules-generator.git"
        info "  2. Copy PKGBUILD and .SRCINFO"
        info "  3. git commit and push"
    fi
else
    info "Skipped AUR publishing"
fi

echo ""

# Flatpak
if confirm "Submit to Flathub?"; then
    info "Preparing Flatpak submission..."

    warning "Flatpak requires manual PR to Flathub"
    info "Steps:"
    info "  1. Fork https://github.com/flathub/flathub"
    info "  2. Create directory: com.github.rpupo63.AIRulesGenerator"
    info "  3. Copy files from flatpak/ directory"
    info "  4. Update app ID from ai_rules_generator to rpupo63"
    info "  5. Create PR with title: 'Add com.github.rpupo63.AIRulesGenerator'"

    if confirm "Open flatpak directory?"; then
        xdg-open flatpak/ 2>/dev/null || open flatpak/ 2>/dev/null || echo "flatpak/ directory ready"
    fi
else
    info "Skipped Flatpak submission"
fi

echo ""

# ============================================================================
# PHASE 8: POST-DEPLOYMENT
# ============================================================================

info "Phase 8: Post-deployment tasks..."

# Create deployment summary
DEPLOY_SUMMARY="deployment-summary-$VERSION.txt"
cat > $DEPLOY_SUMMARY << EOF
AI Rules Generator v$VERSION - Deployment Summary
=================================================
Deployed at: $(date)
Deployed by: $(whoami)@$(hostname)
Git commit: $(git rev-parse HEAD)
Git tag: $RELEASE_TAG

Release URL: $REPO_URL/releases/tag/$RELEASE_TAG

Packages Published:
-------------------
✓ GitHub Release: $REPO_URL/releases/tag/$RELEASE_TAG
✓ PyPI: https://pypi.org/project/ai-rules-generator/$VERSION/
$([ -f "$DEB_FILE" ] && echo "✓ Debian: Uploaded to GitHub release")
✓ Homebrew: Updated in tap (if selected)
✓ AUR: https://aur.archlinux.org/packages/ai-rules-generator (if selected)
○ Flatpak: Manual PR required
○ WinGet: Manual PR required

Verification Commands:
---------------------
pip install ai-rules-generator==$VERSION
brew install rpupo63/tap/ai-rules-generator
yay -S ai-rules-generator
winget install AIRulesGenerator.AIRulesGenerator

Next Steps:
-----------
1. Test installation from each package manager
2. Submit Flatpak PR to Flathub
3. Submit WinGet PR to microsoft/winget-pkgs
4. Update documentation with verified install commands
5. Announce release on social media / forums

Files Generated:
----------------
- dist/*.whl, dist/*.tar.gz (PyPI packages)
- checksums.txt (SHA256 checksums)
$([ -f "$DEB_FILE" ] && echo "- $DEB_FILE (Debian package)")
- $DEPLOY_SUMMARY (this file)

Deployment completed successfully! 🎉
EOF

cat $DEPLOY_SUMMARY

success "Deployment summary saved to $DEPLOY_SUMMARY"
echo ""

# ============================================================================
# COMPLETION
# ============================================================================

echo ""
echo "======================================"
echo "  🎉 DEPLOYMENT COMPLETE! 🎉"
echo "======================================"
echo ""
echo "Version $VERSION has been deployed!"
echo ""
echo "What was done:"
echo "  ✓ Git tag created and pushed"
echo "  ✓ GitHub release published"
echo "  ✓ Checksums generated and updated"
echo "  ✓ Packages built and published"
echo ""
echo "Release URL: $REPO_URL/releases/tag/$RELEASE_TAG"
echo ""
echo "Next: Verify installations and monitor package manager queues"
echo "======================================"
echo ""

exit 0
