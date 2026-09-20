@echo off
rem ============================================================
rem  Build Anakot-Setup.exe (Tauri bootstrap installer)
rem  Runs inside the MSVC x64 dev environment so cargo can find
rem  link.exe + Windows SDK. Rust lives on D: (RUSTUP_HOME/CARGO_HOME).
rem ============================================================
call "D:\VS2022BT\VC\Auxiliary\Build\vcvars64.bat" >nul
set "RUSTUP_HOME=D:\.rustup"
set "CARGO_HOME=D:\.cargo"
set "PATH=D:\.cargo\bin;%PATH%"
cd /d "D:\School\PROJECT\anakot-agent\apps\bootstrap-installer"

echo [build] cargo/rustc:
cargo --version
rustc --version

echo [build] running tauri build --no-bundle ...
call npm run tauri:build -- --no-bundle
set "EXIT=%ERRORLEVEL%"
echo [build] tauri build exit code: %EXIT%
if exist "target\release\Anakot-Setup.exe" (
    echo [build] OUTPUT: target\release\Anakot-Setup.exe
    dir "target\release\Anakot-Setup.exe"
) else (
    echo [build] ERROR: Anakot-Setup.exe not found
)
exit /b %EXIT%
