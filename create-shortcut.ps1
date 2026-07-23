param(
    [string]$ProjectRoot = $PSScriptRoot
)

$Launcher = Join-Path $ProjectRoot "start-hud.ps1"
$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "TianshuHUD.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$sc = $WshShell.CreateShortcut($ShortcutPath)
$sc.TargetPath = "powershell.exe"
$sc.Arguments = "-ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File `"$Launcher`""
$sc.WorkingDirectory = $ProjectRoot
$sc.Description = "Tianshu HUD System Monitor"
$sc.Save()

Write-Host "Shortcut: $ShortcutPath"
