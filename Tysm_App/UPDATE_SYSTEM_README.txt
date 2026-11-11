TYSM GITHUB RELEASE UPDATER — SETUP

1. Create a GitHub repository under your account (public releases).
2. In Tysm_App/tysm_updater.py set GITHUB_REPOSITORY = "YOUR_USERNAME/YOUR_REPOSITORY".
3. Build on Windows by running build_tysm.ps1 from PowerShell.
4. Find BOTH installer_output/Tysm_Setup.exe and Tysm_Setup.exe.sha256.
5. On GitHub: repository > Releases > Draft a new release. Use tag v1.1.0 and attach BOTH files. Publish.
6. Install v1.1.0 locally. Future releases must increment APP_VERSION in tysm_updater.py AND AppVersion in Tysm.iss (v1.2.0, etc), then rebuild and publish both assets.
7. In Tysm click CHECK UPDATES or type /update. Tysm checks the latest public GitHub release. If newer, it asks before downloading, verifies SHA-256, asks again before launching the installer, then exits.

Data is migrated on first launch from old app folder to %LOCALAPPDATA%/Tysm/; keep a backup of your old installation first. Old installer files are not deleted by the migration. The new build does not ship personal JSON/SQLite files. Note: any state files not enumerated for migration may still need manual migration.

SECURITY: SHA-256 detects corruption and mismatches, but because the hash is hosted alongside the installer, it does NOT prove publisher identity if the GitHub release is compromised. Use only your own repository, enable GitHub 2FA, protect release publishing, and never install unexpected releases. The installer is not code-signed.

The installer has NOT been compiled/tested on Windows in this environment.
