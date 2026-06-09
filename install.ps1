# Claude Monitor — one-line Windows installer
#
#   irm https://raw.githubusercontent.com/wyattmcph/wyattmcph-claude-monitor/main/install.ps1 | iex
#
# Downloads the latest standalone executable, puts it on PATH, and creates
# Desktop + Start Menu shortcuts. No Python required.

$ErrorActionPreference = 'Stop'

$Repo    = 'wyattmcph/wyattmcph-claude-monitor'
$Asset   = 'claude-monitor-windows.exe'
$Dir     = Join-Path $env:LOCALAPPDATA 'ClaudeMonitor'
$ExePath = Join-Path $Dir 'claude-monitor.exe'
$Url     = "https://github.com/$Repo/releases/latest/download/$Asset"

Write-Host ""
Write-Host "  Claude Monitor installer" -ForegroundColor Cyan
Write-Host "  ------------------------" -ForegroundColor DarkGray

New-Item -ItemType Directory -Force -Path $Dir | Out-Null

Write-Host "  Downloading the latest release..." -ForegroundColor Gray
Invoke-WebRequest -Uri $Url -OutFile $ExePath

# Add the install dir to the user PATH (so `claude-monitor` works in any terminal)
$UserPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($UserPath -notlike "*$Dir*") {
    [Environment]::SetEnvironmentVariable('Path', "$UserPath;$Dir", 'User')
    Write-Host "  Added to PATH (restart your terminal to use 'claude-monitor')" -ForegroundColor Gray
}

# Create Desktop + Start Menu shortcuts
try {
    $Shell   = New-Object -ComObject WScript.Shell
    $Desktop = [Environment]::GetFolderPath('Desktop')
    $Start   = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'

    foreach ($loc in @("$Desktop\Claude Monitor.lnk", "$Start\Claude Monitor.lnk")) {
        $sc = $Shell.CreateShortcut($loc)
        $sc.TargetPath       = $ExePath
        $sc.WorkingDirectory = $Dir
        $sc.Description       = 'Real-time Claude Code usage monitor'
        $sc.Save()
    }
    Write-Host "  Created Desktop and Start Menu shortcuts" -ForegroundColor Gray
} catch {
    Write-Host "  (Could not create shortcuts — not critical)" -ForegroundColor DarkYellow
}

Write-Host ""
Write-Host "  Installed!  " -ForegroundColor Green -NoNewline
Write-Host "Launch it from the Desktop shortcut, or run:" -ForegroundColor Gray
Write-Host "      claude-monitor" -ForegroundColor White
Write-Host ""
