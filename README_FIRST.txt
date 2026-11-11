TYSM WINDOWS INSTALLER BUILD KIT

This is the full active application flattened out of the latest complete Tysm ZIP, plus Windows build scripts. It is NOT a precompiled Windows installer.

1. On your Windows PC, install Python 3.11 or 3.12 (check Add Python to PATH) and Inno Setup 6 (jrsoftware.org/isinfo.php). Both are free.
2. Extract this entire ZIP to a normal folder such as Desktop\TysmBuild. Do not run it inside the ZIP.
3. Right-click build_tysm.ps1 and choose Run with PowerShell. If execution policy blocks it, open PowerShell in the extracted folder and run:
   powershell -NoProfile -ExecutionPolicy Bypass -File .\build_tysm.ps1
4. After the build, open installer_output\Tysm_Setup.exe and install Tysm.
5. Keep Ollama installed and qwen3:8b downloaded. The installer does NOT bundle the model.

IMPORTANT: BACK UP YOUR EXISTING tysm_memory.json, tysm_history.json, and all other .json/.sqlite3 files BEFORE installing. To migrate your existing memories, copy those files into %LOCALAPPDATA%\Programs\Tysm AFTER installation while Tysm is closed. Do not copy old assistant.py or personality files over the updated ones.

The installer is per-user, needs no admin rights, and keeps JSON/SQLite state files during updates/uninstall. The app still stores user state beside its EXE, so installing in the default per-user location is important. This is an initial packaging approach, not yet a fully tested production installer.

If you get an error, copy the PowerShell error output or send a screenshot. This package has not been compiled or tested on Windows in this environment.
