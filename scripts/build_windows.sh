#!/bin/bash
# Build Windows executables from Linux
# This script provides multiple methods to build Windows executables

set -e

VERSION="${1:-1.0.0}"
METHOD="${2:-wine}"

echo "Building Windows executables for version $VERSION using method: $METHOD"
echo ""

case "$METHOD" in
    wine)
        echo "=== Method 1: Using Wine + PyInstaller ==="
        echo ""
        echo "This method uses Wine to run Windows PyInstaller on Linux."
        echo "Note: This may have limitations and may not work perfectly."
        echo ""
        
        # Check if wine is installed
        if ! command -v wine &> /dev/null; then
            echo "❌ Wine is not installed. Install it with:"
            echo "   sudo pacman -S wine wine-mono wine-gecko"
            echo "   # or on Debian/Ubuntu:"
            echo "   sudo apt install wine wine64"
            exit 1
        fi
        
        # Check if Python is available in Wine
        if ! wine python --version &> /dev/null; then
            echo "❌ Python is not installed in Wine."
            echo "   You need to install Python for Windows in Wine first."
            echo "   Download Python installer and run: wine python-installer.exe"
            exit 1
        fi
        
        echo "Installing PyInstaller in Wine Python..."
        wine pip install pyinstaller
        
        echo "Building executable using spec file..."
        wine pyinstaller ai-rules-generator.spec
        
        echo "✅ Build complete! Executable should be in dist/ai-rules-generator.exe"
        echo "   Rename it to: ai-rules-generator-${VERSION}-win64.exe"
        ;;
        
    docker)
        echo "=== Method 2: Using Docker with Windows container ==="
        echo ""
        echo "⚠️  Note: Docker on Linux cannot run Windows containers."
        echo "   This method requires Docker Desktop on Windows or WSL2."
        echo "   This won't work on native Linux."
        exit 1
        ;;
        
    manual)
        echo "=== Method 3: Manual Build Instructions ==="
        echo ""
        echo "To build on a Windows machine:"
        echo ""
        echo "1. Install Python 3.8+ on Windows"
        echo "2. Clone your repository:"
        echo "   git clone https://github.com/rpupo63/ai-rules-generator.git"
        echo "   cd ai-rules-generator"
        echo ""
        echo "3. Install dependencies:"
        echo "   pip install pyinstaller"
        echo ""
        echo "4. Build the executable:"
        echo "   pyinstaller ai-rules-generator.spec"
        echo ""
        echo "5. Rename and upload:"
        echo "   move dist\\ai-rules-generator.exe ai-rules-generator-${VERSION}-win64.exe"
        echo "   gh release upload v${VERSION} ai-rules-generator-${VERSION}-win64.exe"
        ;;
        
    *)
        echo "Unknown method: $METHOD"
        echo ""
        echo "Available methods:"
        echo "  wine    - Use Wine to run PyInstaller (may have limitations)"
        echo "  manual  - Show instructions for building on Windows"
        echo ""
        echo "Usage: $0 [VERSION] [METHOD]"
        echo "Example: $0 1.0.0 wine"
        exit 1
        ;;
esac

