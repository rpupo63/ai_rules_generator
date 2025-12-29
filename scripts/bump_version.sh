#!/bin/bash
# Usage: ./scripts/bump_version.sh <new_version>
# Example: ./scripts/bump_version.sh 1.0.1

set -e

NEW_VERSION=$1
OLD_VERSION=$(grep -oP '__version__ = "\K[^"]+' ai_rules_generator/__init__.py)

if [ -z "$NEW_VERSION" ]; then
    echo "Usage: $0 <new_version>"
    echo "Current version: $OLD_VERSION"
    exit 1
fi

echo "Bumping version from $OLD_VERSION to $NEW_VERSION"
echo ""

# Update all version files
echo "Updating ai_rules_generator/__init__.py..."
sed -i "s/__version__ = \"$OLD_VERSION\"/__version__ = \"$NEW_VERSION\"/" ai_rules_generator/__init__.py

echo "Updating pyproject.toml..."
sed -i "s/version = \"$OLD_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml

echo "Updating setup.py..."
sed -i "s/version=\"$OLD_VERSION\"/version=\"$NEW_VERSION\"/" setup.py

echo "Updating PKGBUILD..."
sed -i "s/pkgver=$OLD_VERSION/pkgver=$NEW_VERSION/" PKGBUILD

echo "Updating Formula/ai-rules-generator.rb..."
sed -i "s/v$OLD_VERSION/v$NEW_VERSION/g" Formula/ai-rules-generator.rb

echo "Updating flatpak/com.github.ai_rules_generator.AIRulesGenerator.metainfo.xml..."
sed -i "s/version=\"$OLD_VERSION\"/version=\"$NEW_VERSION\"/" flatpak/com.github.ai_rules_generator.AIRulesGenerator.metainfo.xml

# WinGet manifests (if they exist)
if [ -d ".winget/manifests/a/AIRulesGenerator/AIRulesGenerator/$OLD_VERSION" ]; then
    echo "Updating WinGet manifests..."
    for file in .winget/manifests/a/AIRulesGenerator/AIRulesGenerator/$OLD_VERSION/*.yaml; do
        sed -i "s/PackageVersion: $OLD_VERSION/PackageVersion: $NEW_VERSION/" "$file"
        sed -i "s/v$OLD_VERSION/v$NEW_VERSION/g" "$file"
    done
fi

echo ""
echo "✓ Version bumped to $NEW_VERSION"
echo ""
echo "Manual steps remaining:"
echo "1. Update debian/changelog: dch -v ${NEW_VERSION}-1 'New release'"
if [ -d ".winget/manifests/a/AIRulesGenerator/AIRulesGenerator/$OLD_VERSION" ]; then
    echo "2. Rename .winget/manifests/a/AIRulesGenerator/AIRulesGenerator/$OLD_VERSION/ to $NEW_VERSION/"
fi
echo "3. Update flatpak metainfo.xml release date"
echo "4. Review and commit changes"
