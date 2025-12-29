# Deployment Scripts

This directory contains scripts for managing releases and deployments of AI Rules Generator.

## Scripts Overview

### 🚀 `local_deploy.sh` - Complete Local CI/CD Pipeline

The master deployment script that handles the entire release process from your local machine.

**What it does:**

1. **Pre-flight checks** - Validates environment and repository state
2. **Version bumping** - Updates version across all 11 configuration files
3. **Testing** - Validates Python syntax and package building
4. **Git tagging** - Creates annotated tags and pushes to GitHub
5. **GitHub release** - Creates release with auto-generated notes
6. **Checksum generation** - Downloads release artifacts and generates SHA256 checksums
7. **Config updates** - Automatically updates all package manager configs with checksums
8. **Package building** - Builds PyPI packages, Debian .deb
9. **Publishing** - Interactive publishing to all package managers
10. **Post-deployment** - Generates deployment summary report

**Usage:**

```bash
# Deploy current version
./scripts/local_deploy.sh

# Deploy new version
./scripts/local_deploy.sh 1.0.1
```

**Interactive prompts:**

- Version bump confirmation
- Manual step completion verification
- Per-package-manager publishing confirmation

**Outputs:**

- `dist/` - PyPI packages (.whl, .tar.gz)
- `checksums.txt` - SHA256 checksums for all artifacts
- `ai-rules-generator_*.deb` - Debian package (if on Debian/Ubuntu)
- `deployment-summary-VERSION.txt` - Deployment report

---

### ✅ `pre_deploy_check.sh` - Pre-Deployment Validation

Validation script to catch issues before attempting deployment. Run this first!

**What it checks:**

- ✓ Repository structure and core files
- ✓ LICENSE file exists and is MIT
- ✓ No placeholder URLs (`your-username`)
- ✓ Version consistency across all files
- ✓ Python syntax validity
- ✓ Package builds successfully
- ✓ PKGBUILD correctness
- ✓ Git status (uncommitted changes, branch)
- ✓ Required tools availability
- ✓ Checksum placeholders
- ✓ Package manager configs present

**Usage:**

```bash
./scripts/pre_deploy_check.sh
```

**Exit codes:**

- `0` - All checks passed, ready to deploy
- `1` - Critical checks failed, fix before deploying

---

### 🔢 `bump_version.sh` - Version Updater

Updates version number across all 11 configuration files.

**Files updated:**

1. `ai_rules_generator/__init__.py`
2. `pyproject.toml`
3. `setup.py`
4. `PKGBUILD`
5. `Formula/ai-rules-generator.rb`
6. `flatpak/com.github.ai_rules_generator.AIRulesGenerator.metainfo.xml`
9. `.winget/manifests/**/*.yaml` (if exists)

**Usage:**

```bash
./scripts/bump_version.sh 1.0.1
```

**Manual steps after running:**

1. Update `debian/changelog`: `dch -v 1.0.1-1 'New release'`
2. Rename WinGet manifest directory (if applicable)
3. Update flatpak metainfo.xml release date

---

### 🔐 `update_checksums.sh` - Checksum Updater

Reads checksums from `checksums.txt` and updates all package manager configs.

**Prerequisites:**
Must have `checksums.txt` file created with:

```bash
wget https://github.com/rpupo63/ai_rules_generator/archive/refs/tags/vVERSION.tar.gz
wget https://github.com/rpupo63/ai_rules_generator/archive/refs/tags/vVERSION.zip
pip download openai==1.6.1 --no-deps --no-binary :all:
pip download anthropic==0.18.1 --no-deps --no-binary :all:
sha256sum *.tar.gz *.zip > checksums.txt
```

**Files updated:**

- `PKGBUILD` (sha256sums)
- `Formula/ai-rules-generator.rb` (sha256)
- `flatpak/*.yaml` (3 checksums: source, openai, anthropic)

**Usage:**

```bash
./scripts/update_checksums.sh
```

**Next steps after running:**

1. Regenerate .SRCINFO: `makepkg --printsrcinfo > .SRCINFO`
2. Commit changes
3. Push to remote

---

### 📦 `publish_pypi.sh` - Publish to PyPI

Standalone script to publish to PyPI (Python Package Index).

**Usage:**

```bash
./scripts/publish_pypi.sh [version]
```

**What it does:**

- Builds Python packages (wheel and source distribution)
- Uploads to PyPI using twine
- Verifies publication

**Requirements:**

- `twine` installed: `pip install twine`
- PyPI credentials in `~/.pypirc` or environment

---

### 🍺 `publish_homebrew.sh` - Publish to Homebrew Tap

Publishes the formula to your Homebrew tap repository.

**Usage:**

```bash
./scripts/publish_homebrew.sh [version]
```

**What it does:**

- Updates formula in tap repository
- Calculates and updates SHA256 checksum
- Commits and pushes to tap repo

**Requirements:**

- Tap repository: `rpupo63/homebrew-ai-rules-generator`
- Formula file: `Formula/ai-rules-generator.rb`
- Tap cloned at: `~/.package-manager-repos/homebrew-ai-rules-generator`

---

### 🐧 `publish_aur.sh` - Publish to AUR (Arch Linux)

Publishes PKGBUILD to Arch User Repository.

**Usage:**

```bash
./scripts/publish_aur.sh [version]
```

**What it does:**

- Clones AUR repository
- Copies PKGBUILD and generates .SRCINFO
- Commits and pushes to AUR

**Requirements:**

- AUR account with SSH key configured
- Test SSH: `ssh -T aur@aur.archlinux.org`
- `makepkg` for generating .SRCINFO (optional)

---

### 📦 `publish_debian.sh` - Build Debian Package

Builds .deb package and optionally uploads to GitHub releases.

**Usage:**

```bash
./scripts/publish_debian.sh [version]
```

**What it does:**

- Builds .deb package using dpkg-buildpackage
- Optionally uploads to GitHub releases
- Provides PPA upload instructions

**Requirements:**

- Debian/Ubuntu system (or compatible)
- Build tools: `sudo apt install debhelper dh-python python3-all python3-setuptools devscripts`
- `debian/changelog` updated with version

---

### 📦 `publish_flatpak.sh` - Prepare Flatpak

Prepares Flatpak files and provides Flathub submission instructions.

**Usage:**

```bash
./scripts/publish_flatpak.sh [version]
```

**What it does:**

- Validates Flatpak manifest
- Calculates checksums
- Optionally builds package for testing
- Provides Flathub submission instructions

**Requirements:**

- `flatpak-builder` (optional, for testing)
- Manual PR submission to Flathub required

---

### 🪟 `publish_winget.sh` - Prepare WinGet Manifests

Validates WinGet manifests and provides publishing instructions.

**Usage:**

```bash
./scripts/publish_winget.sh [version]
```

**What it does:**

- Validates WinGet manifest files
- Checks for placeholder values
- Provides PR submission instructions

**Requirements:**

- `winget` command (Windows, optional for validation)
- Manual PR submission to microsoft/winget-pkgs required

---

## Typical Deployment Workflow

### First Time Setup

1. **Install required tools:**

   ```bash
   # GitHub CLI
   sudo pacman -S github-cli  # Arch
   brew install gh             # macOS

   # Python build tools
   pip install build twine

   # Package manager tools (platform-specific)
   ```

2. **Configure GitHub CLI:**

   ```bash
   gh auth login
   ```

3. **Set up package manager accounts:**
   - PyPI: Create account at https://pypi.org, generate API token
   - AUR: Set up SSH key at https://aur.archlinux.org
   - Homebrew: Create tap repository
   - Flathub: Fork https://github.com/flathub/flathub

### Regular Release Process

**1. Pre-deployment validation:**

```bash
./scripts/pre_deploy_check.sh
```

Fix any issues reported, then continue.

**2. Run deployment:**

```bash
./scripts/local_deploy.sh 1.0.1
```

**3. Follow interactive prompts:**

- Confirm version bump
- Complete manual steps (debian/changelog, flatpak date)
- Confirm publishing to each package manager
- Enter API keys when prompted

**4. Post-deployment:**

- Review `deployment-summary-VERSION.txt`
- Test installations from each package manager
- Submit Flatpak PR to Flathub

### Hotfix Release Process

For urgent fixes without changing version:

**1. Make fixes and commit:**

```bash
git add .
git commit -m "Fix critical bug"
git push origin main
```

**2. Delete existing tag:**

```bash
git tag -d v1.0.0
git push origin :refs/tags/v1.0.0
gh release delete v1.0.0 --yes
```

**3. Re-deploy:**

```bash
./scripts/local_deploy.sh 1.0.0
```

---

## Individual Package Manager Publishing

You can publish to individual package managers using the dedicated scripts:

```bash
# PyPI
./scripts/publish_pypi.sh 1.0.0

# Homebrew
./scripts/publish_homebrew.sh 1.0.0

# AUR
./scripts/publish_aur.sh 1.0.0

# Debian/Ubuntu
./scripts/publish_debian.sh 1.0.0

# Flatpak (prepare files)
./scripts/publish_flatpak.sh 1.0.0

# WinGet (prepare manifests)
./scripts/publish_winget.sh 1.0.0
```

## Package Manager Specifics

### PyPI

- **Script:** `publish_pypi.sh`
- **Requirements:** `twine`, PyPI API token
- **What's published:** `.whl` and `.tar.gz` from `dist/`
- **Verification:** `pip install ai-rules-generator==VERSION`
- **Update time:** Immediate

### Homebrew

- **Script:** `publish_homebrew.sh`
- **Requirements:** Tap repository at `~/.package-manager-repos/homebrew-ai-rules-generator`
- **What's published:** Formula file
- **Verification:** `brew tap rpupo63/ai-rules-generator && brew install ai-rules-generator`
- **Update time:** Immediate after tap push

### AUR (Arch Linux)

- **Script:** `publish_aur.sh`
- **Requirements:** AUR account, SSH key configured
- **What's published:** PKGBUILD, .SRCINFO
- **Verification:** `yay -S ai-rules-generator`
- **Update time:** Immediate
- **Note:** Must regenerate .SRCINFO after any PKGBUILD changes

### Debian/Ubuntu

- **Script:** `publish_debian.sh`
- **Requirements:** `dpkg-buildpackage`, `debhelper`
- **What's published:** `.deb` file uploaded to GitHub releases
- **Verification:** Download and `sudo dpkg -i ai-rules-generator_*.deb`
- **Update time:** Immediate
- **Note:** For PPA publishing, additional setup required

### Flatpak

- **Script:** `publish_flatpak.sh`
- **Requirements:** Manual PR to Flathub
- **What's published:** Manifest files
- **Verification:** After PR merge, `flatpak install flathub com.github.ai_rules_generator.AIRulesGenerator`
- **Update time:** Varies (days to weeks for review)
- **Note:** Most manual process, requires Flathub PR review

### WinGet

- **Script:** `publish_winget.sh`
- **Requirements:** Manual PR to microsoft/winget-pkgs
- **What's published:** Manifest files
- **Verification:** After PR merge, `winget install AIRulesGenerator.AIRulesGenerator`
- **Update time:** Varies (hours to days for review)

---

## Troubleshooting

### "Tag already exists"

Delete tag locally and remotely:

```bash
git tag -d vVERSION
git push origin :refs/tags/vVERSION
gh release delete vVERSION --yes
```

### "Checksums don't match"

Regenerate checksums:

```bash
rm checksums.txt
./scripts/local_deploy.sh VERSION
```

### "GitHub CLI not authenticated"

```bash
gh auth login
gh auth status
```

### "makepkg failed"

Install build dependencies:

```bash
sudo pacman -S base-devel python-build python-installer python-wheel
```

### "Debian build failed"

Install build tools:

```bash
sudo apt install debhelper dh-python python3-all python3-setuptools
```

### "Can't push to AUR"

Check SSH key:

```bash
ssh -T aur@aur.archlinux.org
# Should respond with: "Hi username! You may use 'git' over ssh."
```

---

## Script Maintenance

### Adding New Package Manager

1. Add config file to repository (e.g., `newpm/package.conf`)
2. Update `bump_version.sh` to include new config
3. Update `update_checksums.sh` if checksums needed
4. Add publishing step to `local_deploy.sh` Phase 7
5. Add validation to `pre_deploy_check.sh`
6. Create publishing script in `scripts/`
7. Update this README

### Updating Dependency Versions

When updating openai/anthropic versions:

1. Update URLs in `update_checksums.sh`
2. Update URLs in `flatpak/*.yaml`
3. Update URLs in `Formula/ai-rules-generator.rb` (if not removed)
4. Regenerate checksums after next release

---

## Security Notes

- **API Keys:** Never commit API keys to the repository
- **SSH Keys:** Keep AUR SSH keys secure
- **GitHub Tokens:** Use fine-grained tokens with minimal permissions
- **Checksums:** Always verify checksums match between source and configs

---

## Additional Resources

- [PUBLISHING.md](../PUBLISHING.md) - Detailed publishing guide
- [DEVELOPMENT.md](../DEVELOPMENT.md) - Development setup
- [Plan file](../.claude/plans/) - Implementation plan reference

---

**Last Updated:** 2024-12-27
**Version:** 1.0.0
