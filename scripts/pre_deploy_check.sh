#!/bin/bash
# Pre-Deployment Validation Script
# Run this before deploying to catch issues early
# Usage: ./scripts/pre_deploy_check.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}[CHECK]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warning() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }

CHECKS_PASSED=0
CHECKS_FAILED=0
WARNINGS=0

check_pass() {
    success "$1"
    ((CHECKS_PASSED++))
}

check_fail() {
    error "$1"
    ((CHECKS_FAILED++))
}

check_warn() {
    warning "$1"
    ((WARNINGS++))
}

echo ""
echo "==========================================="
echo "  Pre-Deployment Validation"
echo "==========================================="
echo ""

# Check 1: Repository structure
info "Checking repository structure..."
if [ -f "ai_rules_generator/__init__.py" ] && [ -f "pyproject.toml" ] && [ -f "setup.py" ]; then
    check_pass "Repository structure valid"
else
    check_fail "Missing core files (run from repo root)"
fi

# Check 2: LICENSE file
info "Checking LICENSE file..."
if [ -f "LICENSE" ]; then
    if grep -q "MIT License" LICENSE; then
        check_pass "LICENSE file exists and is MIT"
    else
        check_warn "LICENSE file exists but may not be MIT"
    fi
else
    check_fail "LICENSE file missing"
fi

# Check 3: No placeholder URLs
info "Checking for placeholder URLs..."
PLACEHOLDERS=$(grep -r "your-username" --include="*.toml" --include="*.yaml" --include="*.rb" --include="*.nuspec" --include="PKGBUILD" . 2>/dev/null | wc -l)
if [ "$PLACEHOLDERS" -eq 0 ]; then
    check_pass "No placeholder URLs found"
else
    check_fail "Found $PLACEHOLDERS files with 'your-username' placeholder"
    grep -r "your-username" --include="*.toml" --include="*.yaml" --include="*.rb" --include="*.nuspec" --include="PKGBUILD" . 2>/dev/null | head -5
fi

# Check 4: Version consistency
info "Checking version consistency..."
VERSION_INIT=$(grep -oP '__version__ = "\K[^"]+' ai_rules_generator/__init__.py)
VERSION_TOML=$(grep -oP 'version = "\K[^"]+' pyproject.toml)
VERSION_SETUP=$(grep -oP 'version="\K[^"]+' setup.py)
VERSION_PKGBUILD=$(grep -oP 'pkgver=\K[^\s]+' PKGBUILD)

if [ "$VERSION_INIT" = "$VERSION_TOML" ] && [ "$VERSION_INIT" = "$VERSION_SETUP" ] && [ "$VERSION_INIT" = "$VERSION_PKGBUILD" ]; then
    check_pass "Version consistent across files: $VERSION_INIT"
else
    check_fail "Version mismatch: __init__=$VERSION_INIT, toml=$VERSION_TOML, setup=$VERSION_SETUP, PKGBUILD=$VERSION_PKGBUILD"
fi

# Check 5: Python syntax
info "Checking Python syntax..."
if python3 -m py_compile ai_rules_generator/*.py 2>/dev/null; then
    check_pass "Python syntax valid"
else
    check_fail "Python syntax errors found"
fi

# Check 6: Package builds
info "Checking if package builds..."
if python3 -m build --outdir /tmp/build-test 2>/dev/null; then
    rm -rf /tmp/build-test
    check_pass "Package builds successfully"
else
    rm -rf /tmp/build-test
    check_fail "Package build failed"
fi

# Check 7: PKGBUILD validation
info "Checking PKGBUILD..."
if [ -f "PKGBUILD" ]; then
    if grep -q "install -Dm644 LICENSE" PKGBUILD; then
        check_pass "PKGBUILD references correct LICENSE path"
    else
        check_fail "PKGBUILD has incorrect LICENSE path"
    fi

    if grep -q "rpupo63" PKGBUILD; then
        check_pass "PKGBUILD has correct maintainer"
    else
        check_warn "PKGBUILD maintainer may need update"
    fi
fi

# Check 8: Git status
info "Checking git status..."
if [ -z "$(git status --porcelain)" ]; then
    check_pass "No uncommitted changes"
else
    check_warn "Uncommitted changes detected"
    git status --short | head -10
fi

# Check 9: On main branch
info "Checking git branch..."
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "main" ]; then
    check_pass "On main branch"
else
    check_warn "On branch '$CURRENT_BRANCH', not 'main'"
fi

# Check 10: Required tools
info "Checking required tools..."
MISSING_TOOLS=()
for tool in git gh python3 pip makepkg; do
    if command -v $tool &> /dev/null; then
        success "  $tool found"
    else
        MISSING_TOOLS+=("$tool")
        warning "  $tool not found"
    fi
done

if [ ${#MISSING_TOOLS[@]} -eq 0 ]; then
    check_pass "All core tools available"
else
    check_warn "Missing tools: ${MISSING_TOOLS[*]}"
fi

# Check 11: Checksum placeholders
info "Checking for checksum placeholders..."
CHECKSUM_PLACEHOLDERS=$(grep -r "REPLACE_WITH_ACTUAL" --include="*.rb" --include="*.ps1" --include="*.yaml" --include="PKGBUILD" . 2>/dev/null | wc -l)
if [ "$CHECKSUM_PLACEHOLDERS" -gt 0 ]; then
    check_warn "Found $CHECKSUM_PLACEHOLDERS checksum placeholders (expected before first release)"
else
    check_pass "No checksum placeholders found"
fi

# Check 12: Package manager configs
info "Checking package manager configs..."
CONFIG_FILES=(
    "pyproject.toml"
    "setup.py"
    "PKGBUILD"
    ".SRCINFO"
    "Formula/ai-rules-generator.rb"
    "debian/control"
    "flatpak/com.github.ai_rules_generator.AIRulesGenerator.yaml"
)

for file in "${CONFIG_FILES[@]}"; do
    if [ -f "$file" ]; then
        success "  $file exists"
    else
        warning "  $file missing"
    fi
done

# Summary
echo ""
echo "==========================================="
echo "  Validation Summary"
echo "==========================================="
echo ""
echo -e "${GREEN}Checks passed: $CHECKS_PASSED${NC}"
echo -e "${YELLOW}Warnings: $WARNINGS${NC}"
echo -e "${RED}Checks failed: $CHECKS_FAILED${NC}"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ Ready for deployment!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Review any warnings above"
    echo "  2. Run: ./scripts/local_deploy.sh $VERSION_INIT"
    exit 0
else
    echo -e "${RED}✗ Fix issues before deploying${NC}"
    echo ""
    echo "Fix the failed checks above, then re-run this script."
    exit 1
fi
