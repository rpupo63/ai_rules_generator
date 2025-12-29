# Debian Package for AI Rules Generator

This directory contains the Debian packaging files for AI Rules Generator.

## Installation

### From PPA (Recommended)

```bash
# Add PPA (once available)
sudo add-apt-repository ppa:rpupo63/ai-rules-generator
sudo apt update
sudo apt install ai-rules-generator
```

### From .deb File

```bash
# Download the .deb file from releases
wget https://github.com/rpupo63/ai-rules-generator/releases/download/v1.0.0/ai-rules-generator_1.0.0-1_all.deb

# Install
sudo apt install ./ai-rules-generator_1.0.0-1_all.deb
```

## Building the Package

### Prerequisites

```bash
sudo apt install debhelper dh-python python3-all python3-setuptools
```

### Build

```bash
# From the project root
dpkg-buildpackage -us -uc -b

# The .deb file will be created in the parent directory
```

### Testing

```bash
# Install locally built package
sudo dpkg -i ../ai-rules-generator_1.0.0-1_all.deb

# Fix dependencies if needed
sudo apt --fix-broken install
```

## Publishing to PPA

1. Sign the package:
   ```bash
   debuild -S -sa
   ```

2. Upload to PPA:
   ```bash
   dput ppa:rpupo63/ai-rules-generator ../ai-rules-generator_1.0.0-1_source.changes
   ```

## File Structure

- `control` - Package metadata and dependencies
- `rules` - Build instructions
- `changelog` - Package changelog
- `compat` - Debhelper compatibility level
- `copyright` - License information
- `install` - Additional files to install

## Resources

- [Debian New Maintainers' Guide](https://www.debian.org/doc/manuals/maint-guide/)
- [Debian Policy Manual](https://www.debian.org/doc/debian-policy/)
- [Ubuntu Packaging Guide](https://packaging.ubuntu.com/html/)
