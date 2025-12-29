#!/bin/bash
# Usage: ./scripts/update_checksums.sh
#
# This script reads checksums from checksums.txt and updates all package manager configs.
# Run this AFTER creating a GitHub release and generating checksums.

set -e

if [ ! -f checksums.txt ]; then
    echo "Error: checksums.txt not found"
    echo ""
    echo "Please create checksums.txt first by running:"
    echo "  wget https://github.com/rpupo63/ai_rules_generator/archive/refs/tags/vVERSION.tar.gz"
    echo "  wget https://github.com/rpupo63/ai_rules_generator/archive/refs/tags/vVERSION.zip"
    echo "  pip download openai==1.6.1 --no-deps --no-binary :all:"
    echo "  pip download anthropic==0.18.1 --no-deps --no-binary :all:"
    echo "  sha256sum *.tar.gz *.zip > checksums.txt"
    exit 1
fi

echo "Reading checksums from checksums.txt..."
echo ""

# Extract checksums
SOURCE_TAR=$(grep -E "v[0-9]+\.[0-9]+\.[0-9]+\.tar\.gz" checksums.txt | awk '{print $1}')
SOURCE_ZIP=$(grep -E "v[0-9]+\.[0-9]+\.[0-9]+\.zip" checksums.txt | awk '{print $1}')
OPENAI=$(grep "openai.*\.tar\.gz" checksums.txt | awk '{print $1}')
ANTHROPIC=$(grep "anthropic.*\.tar\.gz" checksums.txt | awk '{print $1}')

if [ -z "$SOURCE_TAR" ]; then
    echo "Error: Could not find source tarball checksum in checksums.txt"
    exit 1
fi

echo "Source tarball SHA256: $SOURCE_TAR"
echo "Source ZIP SHA256: $SOURCE_ZIP"
echo "OpenAI SHA256: $OPENAI"
echo "Anthropic SHA256: $ANTHROPIC"
echo ""

# Update PKGBUILD
echo "Updating PKGBUILD..."
sed -i "s/sha256sums=('SKIP')/sha256sums=('$SOURCE_TAR')/" PKGBUILD
sed -i "s/sha256sums=('[a-f0-9]\{64\}')/sha256sums=('$SOURCE_TAR')/" PKGBUILD

# Update Homebrew
echo "Updating Formula/ai-rules-generator.rb..."
sed -i "s/sha256 \"REPLACE_WITH_ACTUAL_SHA256\"/sha256 \"$SOURCE_TAR\"/" Formula/ai-rules-generator.rb
sed -i "s/sha256 \"[a-f0-9]\{64\}\"/sha256 \"$SOURCE_TAR\"/" Formula/ai-rules-generator.rb

# Update Flatpak (3 checksums: source, openai, anthropic)
echo "Updating flatpak/com.github.ai_rules_generator.AIRulesGenerator.yaml..."

# Backup the file
cp flatpak/com.github.ai_rules_generator.AIRulesGenerator.yaml flatpak/com.github.ai_rules_generator.AIRulesGenerator.yaml.bak

# Update checksums in order (source, openai, anthropic)
# This uses a more robust approach to replace the 3 different placeholders
awk -v src="$SOURCE_TAR" -v openai="$OPENAI" -v anthropic="$ANTHROPIC" '
/sha256: REPLACE_WITH_ACTUAL_SHA256/ {
    if (!replaced_src) {
        print "        sha256: " src
        replaced_src = 1
        next
    } else if (!replaced_openai) {
        print "        sha256: " openai
        replaced_openai = 1
        next
    } else if (!replaced_anthropic) {
        print "        sha256: " anthropic
        replaced_anthropic = 1
        next
    }
}
/sha256: [a-f0-9]{64}/ {
    if (!replaced_src && /ai_rules_generator/ || /ai-rules-generator/) {
        print "        sha256: " src
        replaced_src = 1
        next
    } else if (!replaced_openai && /openai/) {
        print "        sha256: " openai
        replaced_openai = 1
        next
    } else if (!replaced_anthropic && /anthropic/) {
        print "        sha256: " anthropic
        replaced_anthropic = 1
        next
    }
}
{print}
' flatpak/com.github.ai_rules_generator.AIRulesGenerator.yaml.bak > flatpak/com.github.ai_rules_generator.AIRulesGenerator.yaml

rm flatpak/com.github.ai_rules_generator.AIRulesGenerator.yaml.bak

echo ""
echo "✓ All checksums updated successfully!"
echo ""
echo "Next steps:"
echo "1. Verify changes with: git diff"
echo "2. Regenerate .SRCINFO: makepkg --printsrcinfo > .SRCINFO"
echo "3. Commit changes: git add PKGBUILD .SRCINFO Formula/ flatpak/"
echo "4. Push to remote: git push origin main"
