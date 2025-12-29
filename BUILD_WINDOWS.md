# Building Windows Executables - Alternative Methods

This guide covers alternatives to GitHub Actions for building Windows executables from Linux.

## Quick Summary

Since you're on Linux, here are your options:

1. **Wine + PyInstaller** (Linux) - Can work but may have limitations
2. **Windows VM** - Most reliable, requires Windows license
3. **Remote Windows Build Service** - AppVeyor, Azure Pipelines, etc.
4. **Manual Build on Windows** - If you have access to a Windows machine
5. **Skip Windows Executables** - Just use PyPI (users can install via `pip`)

---

## Method 1: Wine + PyInstaller (Linux)

**Pros**: Works on Linux, no Windows license needed  
**Cons**: May have compatibility issues, requires Wine setup

### Setup

1. Install Wine:

   ```bash
   # Arch Linux
   sudo pacman -S wine wine-mono wine-gecko

   # Debian/Ubuntu
   sudo apt install wine wine64
   ```

2. Install Python for Windows in Wine:

   - Download Python installer from https://www.python.org/downloads/
   - Run: `wine python-3.x.x-amd64.exe`
   - During installation, check "Add Python to PATH"

3. Verify installation:
   ```bash
   wine python --version
   wine pip --version
   ```

### Build

```bash
# Install PyInstaller in Wine Python
wine pip install pyinstaller

# Build using the spec file
wine pyinstaller ai-rules-generator.spec

# The executable will be in dist/ai-rules-generator.exe
# Rename it:
mv dist/ai-rules-generator.exe dist/ai-rules-generator-1.0.0-win64.exe
```

Or use the helper script:

```bash
./scripts/build_windows.sh 1.0.0 wine
```

---

## Method 2: Windows Virtual Machine

**Pros**: Most reliable, native Windows environment  
**Cons**: Requires Windows license, VM setup

### Setup

1. Install a virtualization tool:

   - VirtualBox (free)
   - VMware Workstation
   - QEMU/KVM

2. Install Windows in the VM (requires Windows license)

3. In the Windows VM:

   ```powershell
   # Install Python
   # Download from python.org and install

   # Clone your repo
   git clone https://github.com/rpupo63/ai-rules-generator.git
   cd ai-rules-generator

   # Install PyInstaller
   pip install pyinstaller

   # Build
   pyinstaller ai-rules-generator.spec

   # The executable will be in dist/ai-rules-generator.exe
   ```

---

## Method 3: Remote Windows Build Services

**Pros**: No local Windows setup, automated  
**Cons**: Requires account setup, may have usage limits

### Option A: AppVeyor (Free for open source)

1. Sign up at https://www.appveyor.com/
2. Connect your GitHub repository
3. Create `appveyor.yml`:

```yaml
image: Visual Studio 2019

environment:
  PYTHON: "C:\\Python39"

install:
  - "%PYTHON%\\python.exe -m pip install --upgrade pip"
  - "%PYTHON%\\python.exe -m pip install pyinstaller"

build_script:
  - "%PYTHON%\\python.exe -m pip install ."
  - "%PYTHON%\\Scripts\\pyinstaller.exe ai-rules-generator.spec"

artifacts:
  - path: dist\ai-rules-generator.exe
    name: ai-rules-generator-win64.exe

on_success:
  - appveyor PushArtifact dist\ai-rules-generator.exe
```

### Option B: Azure Pipelines (Free tier available)

1. Sign up at https://azure.microsoft.com/en-us/services/devops/pipelines/
2. Create pipeline YAML similar to GitHub Actions but for Azure

### Option C: GitHub Actions (but you said no to this)

If you change your mind, GitHub Actions is actually the easiest option.

---

## Method 4: Manual Build on Windows Machine

**Pros**: Simple, direct control  
**Cons**: Requires access to Windows machine

### Steps

1. On a Windows machine, install Python 3.8+

2. Clone your repository:

   ```powershell
   git clone https://github.com/rpupo63/ai-rules-generator.git
   cd ai-rules-generator
   ```

3. Install dependencies:

   ```powershell
   pip install pyinstaller
   ```

4. Build:

   ```powershell
   pyinstaller ai-rules-generator.spec
   ```

5. Upload to GitHub release:

   ```powershell
   # Rename
   move dist\ai-rules-generator.exe ai-rules-generator-1.0.0-win64.exe

   # Upload (requires GitHub CLI)
   gh release upload v1.0.0 ai-rules-generator-1.0.0-win64.exe
   ```

---

## Method 5: Skip Windows Executables (Simplest)

**Pros**: No build needed, works immediately  
**Cons**: Users install via pip instead of winget

Windows users can install directly from PyPI:

```powershell
pip install ai-rules-generator
ai-rules-generator --help
```

This works perfectly fine and doesn't require building executables. You can still submit to winget later if you want, or just document PyPI installation for Windows users.

---

## Recommended Approach

For your situation (Linux, no GitHub Actions preference):

1. **Short term**: Use **Method 5** (PyPI only) - it works immediately
2. **Long term**: Set up **Method 2** (Windows VM) or **Method 3** (AppVeyor) for automated builds

---

## Files Created

- `build_entry.py` - Entry point script for PyInstaller
- `ai-rules-generator.spec` - PyInstaller specification file
- `scripts/build_windows.sh` - Helper script for Wine method
- `BUILD_WINDOWS.md` - This guide

---

## Testing the Executable

After building, test on Windows:

```powershell
# Test basic functionality
.\ai-rules-generator.exe --help

# Test init command
.\ai-rules-generator.exe init

# Test generate command
.\ai-rules-generator.exe generate
```

---

## Troubleshooting

### Wine Issues

- If Wine Python can't find modules, ensure you're in the project root
- Try: `wine python -m pip install -e .` to install in development mode
- Check Wine Python path: `wine python -c "import sys; print(sys.path)"`

### PyInstaller Issues

- If missing modules, add them to `hiddenimports` in the spec file
- If data files are missing, check the `datas` section in the spec file
- For debugging, remove `--onefile` temporarily to see the build structure

### Package Data Issues

The spec file includes:

- `awesome-cursorrules/` directory
- `ai_general_guidelines.md` file

If these are missing, verify the paths in the spec file match your project structure.
