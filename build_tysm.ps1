$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host 'Building Tysm for Windows...' -ForegroundColor Cyan
$py = Get-Command py -ErrorAction SilentlyContinue
if ($py) { $python = 'py'; $prefix = @('-3') }
else { $python = 'python'; $prefix = @() }
& $python @prefix -m venv .venv
if ($LASTEXITCODE -ne 0) { throw 'Could not create Python virtual environment. Install Python 3.11 or 3.12 from python.org.' }
$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install pyinstaller pillow ddgs psutil pygetwindow pyautogui requests
if ($LASTEXITCODE -ne 0) { throw 'Python dependencies failed to install.' }
# Keep startup frames, GIFs, audio, personality, and user-state defaults beside assistant.py.
& $venvPython -m PyInstaller --noconfirm --clean --onedir --windowed --name Tysm --contents-directory . --paths Tysm_App --collect-all ddgs --collect-all PIL --add-data 'Tysm_App\assets;assets' --add-data 'Tysm_App\tysm_personality.txt;.' --add-data 'Tysm_App\tysm.png;.' --hidden-import tkinter --hidden-import PIL.ImageTk Tysm_App\assistant.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }
# Bundle all application source modules and initial state alongside the EXE.
Get-ChildItem 'Tysm_App' -File | Where-Object { $_.Extension -in @('.json','.sqlite3') } | ForEach-Object {
  Write-Host "User state file excluded from installation: $($_.Name)"
}
Write-Host ''
Write-Host 'Executable built: dist\Tysm\Tysm.exe' -ForegroundColor Green
$inno = @(
  "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
  "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
  "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $inno) {
  Write-Host 'Install Inno Setup 6 from jrsoftware.org, then rerun this script to generate the installer.' -ForegroundColor Yellow
  exit 0
}
& $inno 'Tysm.iss'
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }
Write-Host 'Installer ready in: installer_output\Tysm_Setup.exe' -ForegroundColor Green
$hash = (Get-FileHash 'installer_output\Tysm_Setup.exe' -Algorithm SHA256).Hash.ToLowerInvariant()
Set-Content -Path 'installer_output\Tysm_Setup.exe.sha256' -Value "$hash  Tysm_Setup.exe" -Encoding ascii
Write-Host 'Checksum ready: installer_output\Tysm_Setup.exe.sha256' -ForegroundColor Green
