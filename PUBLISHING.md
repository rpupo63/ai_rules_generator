# Publishing Guide for All Package Managers

This guide covers how to publish ai-rules-generator to all major package managers.

## Pre-Publishing Checklist

Before publishing to any package manager:

1. **Update Version Numbers**

   - [ ] `pyproject.toml` - Update version
   - [ ] `setup.py` - Update version
   - [ ] `PKGBUILD` - Update pkgver
   - [ ] `Formula/ai-rules-generator.rb` - Update version in url

2. **Update URLs**

   - [ ] Replace `rpupo63` with your actual GitHub username in all files
   - [ ] Verify all GitHub URLs are correct

3. **Update Package Manager Files**

   - [ ] `debian/changelog` - Update version and date
   - [ ] `.winget/manifests/*/1.0.0/*.yaml` - Update version
   - [ ] `flatpak/com.github.ai_rules_generator.AIRulesGenerator.yaml` - Update version

4. **Create Git Tag and Release**

   ```bash
   git tag -a v1.0.0 -m "Release v1.0.0"
   git push origin v1.0.0
   ```

   - [ ] Create GitHub release from tag
   - [ ] Add release notes

5. **Calculate Checksums**

   ```bash
   # Download release
   curl -L -o ai-rules-generator-1.0.0.tar.gz \
     https://github.com/YOUR-USERNAME/ai-rules-generator/archive/v1.0.0.tar.gz

   # Calculate SHA256
   sha256sum ai-rules-generator-1.0.0.tar.gz
   ```

   - [ ] Update checksum in PKGBUILD
   - [ ] Update checksum in Homebrew formula

---

## 1. PyPI (pip) - Widest Reach

PyPI is the Python Package Index - accessible to all pip users.

### Setup (First Time)

1. Create PyPI account:

   - https://pypi.org/account/register/

2. Generate API token:

   - Go to https://pypi.org/manage/account/token/ and create a token
   - Tokens should start with `pypi-`

   **Token Scope Recommendation**:

   - **Recommended**: Create a **project-scoped token** (select the specific project: `ai-rules-generator`)
   - **Why**: Better security - if compromised, only this project is affected, not your entire account
   - **Alternative**: Account-wide token works too, but has broader permissions
   - Both work for publishing; project-scoped is just more secure

3. Install build tools:

   ```bash
   pip install build twine
   ```

4. Configure authentication:

   Create `~/.pypirc`:

   ```ini
   [distutils]
   index-servers =
       pypi

   [pypi]
   username = __token__
   password = pypi-YOUR_PYPI_TOKEN_HERE
   ```

   Make it secure:

   ```bash
   chmod 600 ~/.pypirc
   ```

### Publishing

```bash
# Build the package
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

### Troubleshooting Authentication Errors

If you get a `403 Forbidden` error:

1. **Check your token format**

   - Token should start with `pypi-`
   - Include the full token (including the `pypi-` prefix) as the password
   - Username should be exactly `__token__` (with underscores)

2. **Verify token permissions**

   - Make sure the token has upload/upload:pypi scope enabled
   - If needed, generate a new token with proper permissions

3. **Test with verbose output**
   ```bash
   python -m twine upload dist/* --verbose
   ```

### Verification

```bash
pip install ai-rules-generator
ai-rules-generator --help
```

**Status**: ✅ Ready to publish

---

## 2. Homebrew (macOS/Linux) - Popular on Mac

Homebrew is the most popular package manager for macOS.

**Important**: Homebrew requires a **separate GitHub repository** called a "tap" that contains only the formula file. This is different from your main app repository:

- **Main app repo**: `rpupo63/ai-rules-generator` (contains your code)
- **Tap repo**: `rpupo63/homebrew-ai-rules-generator` (contains only the `.rb` formula file)

The formula in the tap points to releases in your main repo. This is how Homebrew works - taps are separate repositories.

**Alternative**: You can skip Homebrew entirely if you only want PyPI distribution, or submit to Homebrew's official core repository (requires approval).

### Setup (First Time)

1. Create a GitHub repository for your tap:

   ```bash
   # Create repo: homebrew-ai-rules-generator
   # On GitHub: rpupo63/homebrew-ai-rules-generator
   # This is a SEPARATE repo from your main app repo
   # It will only contain the formula file (.rb)
   ```

2. Clone the tap locally:

   ```bash
   # From your main repo root
   mkdir -p .package-manager-repos
   git clone https://github.com/rpupo63/homebrew-ai-rules-generator.git .package-manager-repos/homebrew-ai-rules-generator
   cd .package-manager-repos/homebrew-ai-rules-generator
   ```

   **Note**: The `.package-manager-repos/` directory is gitignored, so these clones won't be tracked in your main repository.

### Publishing

1. Copy the formula (from your main repo root):

   ```bash
   cp Formula/ai-rules-generator.rb .package-manager-repos/homebrew-ai-rules-generator/
   cd .package-manager-repos/homebrew-ai-rules-generator
   ```

2. Update the formula with correct checksums:

   ```bash
   # Download release tarball
   curl -L -o /tmp/ai-rules-generator-1.0.0.tar.gz \
     https://github.com/rpupo63/ai-rules-generator/archive/v1.0.0.tar.gz

   # Calculate checksum (macOS)
   shasum -a 256 /tmp/ai-rules-generator-1.0.0.tar.gz | awk '{print $1}'

   # OR on Linux
   sha256sum /tmp/ai-rules-generator-1.0.0.tar.gz | awk '{print $1}'

   # Copy the hash (first 64 hex characters) and update sha256 in the formula
   ```

3. Test the formula locally:

   ```bash
   brew install --build-from-source ./ai-rules-generator.rb
   brew test ai-rules-generator
   ai-rules-generator --help
   ```

4. Push to GitHub:
   ```bash
   git add ai-rules-generator.rb
   git commit -m "Add ai-rules-generator v1.0.0"
   git push origin main
   ```

### User Installation

```bash
brew tap rpupo63/ai-rules-generator
brew install ai-rules-generator
```

**Status**: ✅ Ready to publish (need to create tap repo)

---

## 3. AUR (Arch Linux) - Linux Community

AUR is the Arch User Repository for Arch Linux users.

### Setup (First Time)

1. Create AUR account: https://aur.archlinux.org/register

2. Add SSH key to AUR account:

   - Go to your AUR account settings: https://aur.archlinux.org/account/
   - Add your SSH public key

3. Test SSH connection:

   ```bash
   ssh -T aur@aur.archlinux.org
   # Should respond: "Hi username! You may use 'git' over ssh."
   ```

4. Clone the AUR repository (this creates the repository if it doesn't exist):

   ```bash
   # From your main repo root
   mkdir -p .package-manager-repos
   git clone ssh://aur@aur.archlinux.org/ai-rules-generator.git .package-manager-repos/aur-ai-rules-generator
   cd .package-manager-repos/aur-ai-rules-generator
   ```

   **Note**: AUR's Git server automatically creates the repository when you clone it (if it doesn't already exist). No separate "create repository" step is needed - the clone command handles this. The `.package-manager-repos/` directory is gitignored, so these clones won't be tracked in your main repository.

### Publishing

1. Copy PKGBUILD to AUR repository (from your main repo root):

   ```bash
   cp PKGBUILD .package-manager-repos/aur-ai-rules-generator/
   cd .package-manager-repos/aur-ai-rules-generator
   ```

2. Generate .SRCINFO:

   ```bash
   makepkg --printsrcinfo > .SRCINFO
   ```

3. Test build:

   ```bash
   makepkg -si
   ai-rules-generator --help
   ```

4. Commit and push:
   ```bash
   git add PKGBUILD .SRCINFO
   git commit -m "Initial commit: ai-rules-generator v1.0.0"
   git push
   ```

### User Installation

```bash
yay -S ai-rules-generator
# or
paru -S ai-rules-generator
```

**Status**: ✅ Ready to publish (need AUR account)

---

## 4. winget (Windows) - Official Windows Package Manager

winget is the official Windows Package Manager from Microsoft.

**✅ Good News**: You **CAN** prepare and submit WinGet manifests from Linux! Manifest files are just YAML and can be created/edited on any platform. Only validation and user installation require Windows.

**⚠️ Important**: Winget requires Windows executables (`.exe` files) for Python packages. You have two options:

### Option A: Build Windows Executables (Recommended)

Build Windows executables using PyInstaller or similar tools, then upload them to GitHub releases.

#### Building Windows Executables

**See `BUILD_WINDOWS.md` for detailed instructions on building Windows executables from Linux.**

Quick summary:

1. **On a Windows machine**, install PyInstaller:

   ```powershell
   pip install pyinstaller
   ```

2. Build using the spec file:

   ```powershell
   pyinstaller ai-rules-generator.spec
   ```

3. Upload to GitHub release:

   ```bash
   gh release upload v1.0.0 dist/ai-rules-generator.exe --rename ai-rules-generator-1.0.0-win64.exe
   ```

**Alternative methods** (Wine, VM, remote services) are documented in `BUILD_WINDOWS.md`.

### Option B: Use PyPI Directly (Simpler, but not via winget)

Users can install directly from PyPI:

```powershell
pip install ai-rules-generator
```

This doesn't require winget, but provides the same functionality.

### Setup (First Time)

1. Fork the winget-pkgs repository: https://github.com/microsoft/winget-pkgs

2. Clone your fork:

   ```bash
   # From your main repo root
   mkdir -p .package-manager-repos
   git clone https://github.com/YOUR-USERNAME/winget-pkgs.git .package-manager-repos/winget-pkgs
   ```

**Note**: The `wingetcreate` tool (Windows-only) is optional. You can create and edit manifests manually using the templates in `.winget/manifests/`.

### Publishing (After Building Windows Executables)

1. Download the Windows executables from your GitHub release:

   ```bash
   # Download the Windows executables
   wget https://github.com/rpupo63/ai-rules-generator/releases/download/v1.0.0/ai-rules-generator-1.0.0-win64.exe
   wget https://github.com/rpupo63/ai-rules-generator/releases/download/v1.0.0/ai-rules-generator-1.0.0-win32.exe
   ```

2. Calculate SHA256 hashes (Linux):

   ```bash
   # For x64 executable
   sha256sum ai-rules-generator-1.0.0-win64.exe | awk '{print $1}'

   # For x86 executable (if built)
   sha256sum ai-rules-generator-1.0.0-win32.exe | awk '{print $1}'
   ```

3. Update SHA256 hashes in `.winget/manifests/a/AIRulesGenerator/AIRulesGenerator/1.0.0/AIRulesGenerator.AIRulesGenerator.installer.yaml` with the hash values from step 2.

4. Copy manifest files to your fork:

   ```bash
   # From your main repo root
   cp -r .winget/manifests/a/AIRulesGenerator .package-manager-repos/winget-pkgs/manifests/a/
   cd .package-manager-repos/winget-pkgs
   ```

5. (Optional) Validate manifests on Windows:

   If you have access to a Windows machine, you can validate the manifests:

   ```powershell
   winget validate --manifest manifests/a/AIRulesGenerator/AIRulesGenerator/1.0.0/
   ```

   **Note**: Validation is optional - GitHub Actions will automatically validate when you submit the PR.

6. Create pull request:

   ```bash
   git add manifests/a/AIRulesGenerator/AIRulesGenerator/1.0.0/
   git commit -m "Add AIRulesGenerator.AIRulesGenerator version 1.0.0"
   git push origin main
   # Then create PR on GitHub web interface
   ```

7. Wait for automated tests and maintainer approval

### User Installation (Windows Only)

Users on Windows can install with:

```powershell
winget install AIRulesGenerator.AIRulesGenerator
```

**Status**: ⚠️ Need to build Windows executables first, then ready to publish

---

## 5. APT (Debian/Ubuntu) - Debian Package Manager

APT packages work on Debian, Ubuntu, and derivatives.

### Setup (First Time)

1. Create Launchpad account: https://launchpad.net/

2. Set up GPG key for signing:

   ```bash
   gpg --gen-key
   gpg --list-keys
   gpg --keyserver keyserver.ubuntu.com --send-keys YOUR-KEY-ID
   ```

3. Create PPA on Launchpad:
   - Go to https://launchpad.net/~rpupo63
   - Click "Create a new PPA"
   - Name: `ai-rules-generator`

### Publishing

1. Install build tools:

   ```bash
   sudo apt install debhelper dh-python python3-all python3-setuptools devscripts
   ```

2. Build source package:

   ```bash
   # From project root
   debuild -S -sa
   ```

3. Upload to PPA:

   ```bash
   dput ppa:rpupo63/ai-rules-generator ../ai-rules-generator_1.0.0-1_source.changes
   ```

4. Wait for PPA to build (Launchpad builds for multiple Ubuntu versions)

### Alternative: Direct .deb Distribution

```bash
# Build .deb package
dpkg-buildpackage -us -uc -b

# Upload .deb to GitHub releases
gh release upload v1.0.0 ../ai-rules-generator_1.0.0-1_all.deb
```

### User Installation

```bash
# From PPA
sudo add-apt-repository ppa:rpupo63/ai-rules-generator
sudo apt update
sudo apt install ai-rules-generator

# From .deb file
wget https://github.com/rpupo63/ai-rules-generator/releases/download/v1.0.0/ai-rules-generator_1.0.0-1_all.deb
sudo apt install ./ai-rules-generator_1.0.0-1_all.deb
```

**Status**: ✅ Ready to publish (need Launchpad account and PPA)

---

## 6. Flatpak (Linux Universal) - Cross-Distribution Package

Flatpak works across most Linux distributions.

### Setup (First Time)

1. Install flatpak-builder:

   ```bash
   sudo apt install flatpak flatpak-builder
   ```

2. Add Flathub repository:

   ```bash
   flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
   ```

3. Install required runtimes:
   ```bash
   flatpak install flathub org.freedesktop.Platform//23.08 org.freedesktop.Sdk//23.08
   ```

### Publishing

1. Update SHA256 hashes in `flatpak/com.github.ai_rules_generator.AIRulesGenerator.yaml`:

   ```bash
   # For main source
   sha256sum ai-rules-generator-1.0.0.tar.gz

   # For Python dependencies
   sha256sum openai-1.6.1.tar.gz
   sha256sum anthropic-0.18.1.tar.gz
   ```

2. Build Flatpak:

   ```bash
   cd flatpak
   flatpak-builder --force-clean build-dir com.github.ai_rules_generator.AIRulesGenerator.yaml
   ```

3. Test the build:

   ```bash
   flatpak-builder --run build-dir com.github.ai_rules_generator.AIRulesGenerator.yaml ai-rules-generator --help
   ```

4. Create bundle for direct distribution:

   ```bash
   flatpak-builder --repo=repo --force-clean build-dir com.github.ai_rules_generator.AIRulesGenerator.yaml
   flatpak build-bundle repo ai-rules-generator-1.0.0.flatpak com.github.ai_rules_generator.AIRulesGenerator

   # Upload to GitHub releases
   gh release upload v1.0.0 ai-rules-generator-1.0.0.flatpak
   ```

5. **Submit to Flathub** (for official distribution):
   - Fork https://github.com/flathub/flathub
   - Create new repository: `com.github.ai_rules_generator.AIRulesGenerator`
   - Add manifest and metadata files
   - Create PR to Flathub

### User Installation

```bash
# From Flathub (after approval)
flatpak install flathub com.github.ai_rules_generator.AIRulesGenerator

# From .flatpak bundle
flatpak install --user ai-rules-generator-1.0.0.flatpak
```

**Status**: ✅ Ready to publish (bundle ready, Flathub submission pending)

---

## 7. Snap (Linux - Optional)

Snap packages work across many Linux distributions.

### Setup

Create `snap/snapcraft.yaml`:

```yaml
name: ai-rules-generator
version: "1.0.0"
summary: Generate AI coding agent rules
description: |
  A CLI tool that generates comprehensive AI coding agent rules for
  Cursor and Claude Code based on your project configuration.

base: core22
confinement: strict
grade: stable

apps:
  ai-rules-generator:
    command: bin/ai-rules-generator
    plugs: [home, network]
  ai-rules:
    command: bin/ai-rules
    plugs: [home, network]

parts:
  ai-rules-generator:
    plugin: python
    source: .
    python-packages:
      - .
```

### Publishing

```bash
snapcraft
snapcraft upload --release=stable ai-rules-generator_1.0.0_amd64.snap
```

---

## Quick Release Checklist

When releasing a new version:

- [ ] 1. Update version in all files (pyproject.toml, setup.py, PKGBUILD, formula, nuspec)
- [ ] 2. Update CHANGELOG.md
- [ ] 3. Commit changes: `git commit -am "Release v1.0.0"`
- [ ] 4. Create tag: `git tag -a v1.0.0 -m "Release v1.0.0"`
- [ ] 5. Push: `git push && git push --tags`
- [ ] 6. Create GitHub release
- [ ] 7. Calculate checksums for all package managers
- [ ] 8. Publish to PyPI: `python -m build && twine upload dist/*`
- [ ] 9. Update Homebrew formula and push to tap
- [ ] 10. Update AUR PKGBUILD and push
- [ ] 11. Create PR to winget-pkgs with updated manifests
- [ ] 13. Build and upload .deb package to PPA
- [ ] 14. Build and upload Flatpak bundle to GitHub releases
- [ ] 15. Submit Flatpak to Flathub (if first release)
- [ ] 16. Announce release (GitHub, social media, etc.)

---

## Testing Across Platforms

### Linux (Arch)

```bash
yay -S ai-rules-generator
ai-rules-generator init
```

### Linux (Other)

```bash
pip install ai-rules-generator
ai-rules-generator init
```

### macOS

```bash
brew tap rpupo63/ai-rules-generator
brew install ai-rules-generator
ai-rules-generator init
```

### Windows (winget)

```powershell
winget install AIRulesGenerator.AIRulesGenerator
ai-rules-generator init
```

### Linux (Debian/Ubuntu)

```bash
sudo apt install ai-rules-generator
ai-rules-generator init
```

### Linux (Flatpak)

```bash
flatpak install flathub com.github.ai_rules_generator.AIRulesGenerator
flatpak run com.github.ai_rules_generator.AIRulesGenerator init
```

All platforms should:

1. Install successfully
2. Run `ai-rules-generator init` interactively
3. Store config in the correct platform location
4. Work without manual environment variable setup

---

## Support Matrix

| Platform              | Package Manager | Status      | Auto-Update |
| --------------------- | --------------- | ----------- | ----------- |
| macOS                 | Homebrew        | ✅ Ready    | Yes         |
| Linux (Arch)          | AUR (yay/paru)  | ✅ Ready    | Yes         |
| Linux (Debian/Ubuntu) | APT (PPA)       | ✅ Ready    | Yes         |
| Linux (Universal)     | Flatpak         | ✅ Ready    | Yes         |
| Linux (All)           | pip             | ✅ Ready    | Manual      |
| Windows               | winget          | ✅ Ready    | Yes         |
| Windows               | pip             | ✅ Ready    | Manual      |
| Linux (All)           | Snap            | 📝 Optional | Yes         |

---

## Automation (Future)

Consider setting up GitHub Actions to:

- Automatically build and test on all platforms
- Publish to PyPI on release
- Update Homebrew formula automatically

Example `.github/workflows/release.yml` can automate much of this process.
