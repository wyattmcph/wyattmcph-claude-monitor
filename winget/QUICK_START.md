# winget Manifest Quick Start Guide

## 📦 What is This?

The files in this directory are Windows Package Manager (winget) manifests for Claude Monitor. They enable users to install Claude Monitor on Windows with a simple command:

```powershell
winget install wyattmcph.ClaudeMonitor
```

## 🚀 Current Status

✅ **v3.5.0 manifest is ready** for submission to the Windows Package Manager Community Repository.

The manifest includes:
- Package metadata
- Windows installer information
- SHA256 hash of the executable
- Release notes and feature descriptions
- Publisher and repository links

## 📋 Files in This Directory

```
winget/
├── QUICK_START.md                          ← You are here
├── WINGET_SUBMISSION.md                    ← Full submission guide
├── update-manifest.ps1                     ← Script to update manifests
└── wyattmcph.ClaudeMonitor/
    └── 3.5.0/
        ├── wyattmcph.ClaudeMonitor.yaml                    (metadata)
        ├── wyattmcph.ClaudeMonitor.installer.yaml          (installer info)
        └── wyattmcph.ClaudeMonitor.locale.en-US.yaml       (description)
```

## ⚡ Quick Actions

### Update Manifest for New Release

When you release a new version:

```powershell
# Update to latest version (auto-downloads binary)
.\update-manifest.ps1

# Or specify a version
.\update-manifest.ps1 -Version 3.6.0

# Or use a local binary file
.\update-manifest.ps1 -BinaryPath "C:\path\to\claude-monitor-windows.exe"
```

The script will:
1. Download the binary (or use provided one)
2. Calculate SHA256 hash
3. Update all manifest files
4. Display next steps

### Manual Hash Calculation

If you need to calculate the hash manually:

```powershell
# PowerShell
$hash = (Get-FileHash -Path "claude-monitor-windows.exe" -Algorithm SHA256).Hash
Write-Host $hash

# Or using certutil (built-in)
certutil -hashfile "claude-monitor-windows.exe" SHA256
```

## 📝 Submission Checklist

Before submitting to winget-pkgs:

- [ ] Binary is built and released on GitHub
- [ ] SHA256 hash is calculated and correct
- [ ] Manifest files are updated with new version
- [ ] Release notes are accurate in locale manifest
- [ ] All YAML files have correct syntax (validate with a YAML linter)
- [ ] URLs are correct and accessible
- [ ] ReadTheDocs or license link is valid

## 🔗 Submission Process

1. **Fork** [microsoft/winget-pkgs](https://github.com/microsoft/winget-pkgs)
2. **Copy** the manifest directory to your fork:
   ```
   manifests/w/wyattmcph/ClaudeMonitor/3.5.0/
   ```
3. **Test** locally with winget if available
4. **Create** a pull request with clear description
5. **Address** any review comments
6. **Merge** - once approved, users can install!

See `WINGET_SUBMISSION.md` for detailed instructions.

## ✅ After Submission

Once your manifest is approved and published in the community repository:

**Users can install with:**
```powershell
winget install wyattmcph.ClaudeMonitor
```

**Users can update with:**
```powershell
winget upgrade wyattmcph.ClaudeMonitor
```

**Users can search for it with:**
```powershell
winget search claude-monitor
winget show wyattmcph.ClaudeMonitor
```

## 🆘 Troubleshooting

### Invalid YAML Syntax
- Check indentation (use spaces, not tabs)
- Ensure colons are followed by spaces
- Validate with online YAML validator

### Hash Mismatch
- Re-download the binary from the GitHub release
- Recalculate using the script or manual method
- Update the `.installer.yaml` file

### URL Issues
- Verify GitHub release URL is correct
- Ensure binary exists at that URL
- Test URL in browser to confirm accessibility

### Schema Validation
- Use [JSON Schema Validator](https://json.schemastore.org/)
- Reference: `https://aka.ms/winget-manifest.schema.json`

## 📚 Resources

- [Windows Package Manager Docs](https://docs.microsoft.com/en-us/windows/package-manager/)
- [winget-pkgs Repository](https://github.com/microsoft/winget-pkgs)
- [Community Repository Guidelines](https://github.com/microsoft/winget-pkgs/blob/master/CONTRIBUTING.md)
- [Manifest Schema](https://github.com/microsoft/winget-cli/tree/master/schemas)

## 💡 Pro Tips

1. **Automate Future Updates**: Create a GitHub Actions workflow that updates the manifest and creates a PR to winget-pkgs automatically on each release.

2. **Version Tracking**: Keep previous versions in separate directories:
   ```
   wyattmcph.ClaudeMonitor/
   ├── 3.4.2/
   ├── 3.5.0/
   └── 3.6.0/
   ```

3. **Documentation**: Include a `.gitignore` in this directory to exclude downloaded binaries:
   ```
   *.exe
   !claude-monitor-*.exe  (if you want to track specific versions)
   ```

4. **Testing**: Before submitting, test with:
   ```powershell
   winget validate .\wyattmcph.ClaudeMonitor\3.5.0\
   ```

## 🎯 Next Steps

1. ✅ Manifest files are ready
2. 📥 Wait for v3.5.0 release and binary build
3. 🔄 Run `update-manifest.ps1` to update SHA256 hash
4. 📤 Fork winget-pkgs and create PR
5. ⏳ Wait for community review and approval
6. 🎉 Users can now install via winget!

---

**Last Updated:** June 5, 2026  
**Current Version:** 3.5.0  
**Status:** Ready for submission
