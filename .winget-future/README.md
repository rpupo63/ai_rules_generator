# Winget Package Manifests

This directory contains the Windows Package Manager (winget) manifest files for AI Rules Generator.

## Installation

```powershell
winget install AIRulesGenerator.AIRulesGenerator
```

## Publishing to winget

1. Fork the [winget-pkgs repository](https://github.com/microsoft/winget-pkgs)
2. Copy the manifest files from `.winget/manifests/` to `manifests/a/AIRulesGenerator/AIRulesGenerator/1.0.0/`
3. Update the SHA256 hashes in the installer manifest
4. Create a pull request

## Updating SHA256 Hashes

After downloading the Windows executables from your GitHub release:

```bash
# Download executables (if not already downloaded)
wget https://github.com/rpupo63/ai-rules-generator/releases/download/v1.0.0/ai-rules-generator-1.0.0-win64.exe
wget https://github.com/rpupo63/ai-rules-generator/releases/download/v1.0.0/ai-rules-generator-1.0.0-win32.exe

# Calculate SHA256 hashes (Linux)
# For x64
sha256sum ai-rules-generator-1.0.0-win64.exe

# For x86
sha256sum ai-rules-generator-1.0.0-win32.exe
```

Update the `InstallerSha256` fields in `AIRulesGenerator.AIRulesGenerator.installer.yaml` with the hash values (first 64 hex characters).

## Manifest Structure

- `AIRulesGenerator.AIRulesGenerator.yaml` - Version manifest
- `AIRulesGenerator.AIRulesGenerator.installer.yaml` - Installer details
- `AIRulesGenerator.AIRulesGenerator.locale.en-US.yaml` - Package metadata

## Resources

- [winget-pkgs repository](https://github.com/microsoft/winget-pkgs)
- [Manifest documentation](https://docs.microsoft.com/en-us/windows/package-manager/package/)
- [wingetcreate tool](https://github.com/microsoft/winget-create)
