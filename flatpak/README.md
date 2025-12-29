# Flatpak Package for AI Rules Generator

This directory contains the Flatpak manifest and metadata files for AI Rules Generator.

## Installation

### From Flathub (Once Available)

```bash
flatpak install flathub com.github.ai_rules_generator.AIRulesGenerator
```

### From .flatpak File

```bash
# Download the .flatpak file from releases
wget https://github.com/rpupo63/ai-rules-generator/releases/download/v1.0.0/ai-rules-generator-1.0.0.flatpak

# Install
flatpak install --user ai-rules-generator-1.0.0.flatpak
```

## Running

```bash
flatpak run com.github.ai_rules_generator.AIRulesGenerator
```

## Building the Flatpak

### Prerequisites

```bash
# Install flatpak and flatpak-builder
sudo apt install flatpak flatpak-builder

# Add Flathub repository
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo

# Install required runtimes
flatpak install flathub org.freedesktop.Platform//23.08 org.freedesktop.Sdk//23.08
```

### Build

```bash
# From the flatpak directory
flatpak-builder --force-clean build-dir com.github.ai_rules_generator.AIRulesGenerator.yaml

# Test the build
flatpak-builder --run build-dir com.github.ai_rules_generator.AIRulesGenerator.yaml ai-rules-generator --help
```

### Create Bundle

```bash
# Create a .flatpak bundle for distribution
flatpak-builder --repo=repo --force-clean build-dir com.github.ai_rules_generator.AIRulesGenerator.yaml
flatpak build-bundle repo ai-rules-generator-1.0.0.flatpak com.github.ai_rules_generator.AIRulesGenerator
```

## Publishing to Flathub

1. Fork the [Flathub repository](https://github.com/flathub/flathub)
2. Create a new repository for your app: `com.github.ai_rules_generator.AIRulesGenerator`
3. Add the manifest file and metadata
4. Update SHA256 hashes for all source files
5. Create a pull request to Flathub

## Updating SHA256 Hashes

```bash
# For the source tarball
sha256sum ai-rules-generator-1.0.0.tar.gz

# For Python packages
sha256sum openai-1.6.1.tar.gz
sha256sum anthropic-0.18.1.tar.gz
```

Update the `sha256` fields in the manifest with the output.

## File Structure

- `com.github.ai_rules_generator.AIRulesGenerator.yaml` - Flatpak manifest
- `com.github.ai_rules_generator.AIRulesGenerator.desktop` - Desktop entry
- `com.github.ai_rules_generator.AIRulesGenerator.metainfo.xml` - AppStream metadata
- `com.github.ai_rules_generator.AIRulesGenerator.svg` - Application icon

## Resources

- [Flatpak Documentation](https://docs.flatpak.org/)
- [Flathub Submission Guidelines](https://github.com/flathub/flathub/wiki/App-Submission)
- [AppStream Metadata Guidelines](https://www.freedesktop.org/software/appstream/docs/)
