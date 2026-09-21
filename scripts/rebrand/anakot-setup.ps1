# ==============================================================================
# anakot-setup.ps1 -- Full setup & upstream sync for Anakot Agent
#
# Workflows:
#   1. Sync (-Mode Sync): Pull latest Anakot upstream, merge, rebrand, patch, & test
#   2. Fresh (-Mode Fresh): Clone fresh from Anakot upstream, rebrand, & install
#   3. Rebrand (-Mode RebrandOnly): Re-run rebrand.py and custom_patches.py in-place
#
# Usage:
#   .\scripts\rebrand\anakot-setup.ps1 -Mode Sync
#   .\scripts\rebrand\anakot-setup.ps1 -Mode Fresh -TargetDir "..\anakot-agent-fresh"
#   .\scripts\rebrand\anakot-setup.ps1 -Mode RebrandOnly
# ==============================================================================

[CmdletBinding()]
param(
    [ValidateSet("Sync", "Fresh", "RebrandOnly")]
    [string]$Mode = "Sync",

    [string]$TargetDir = "",

    [string]$UpstreamRepo = "https://github.com/NousResearch/hermes-agent.git",

    [string]$ForkRepo = "https://github.com/Chensihakniroth/anakot-agent-v1.git",

    [switch]$SkipBuild,

    [switch]$BuildBootstrap,

    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Resolve directories
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$DefaultRoot = Resolve-Path (Join-Path $ScriptDir "..\..") | Select-Object -ExpandProperty Path

if ([string]::IsNullOrWhiteSpace($TargetDir)) {
    if ($Mode -eq "Fresh") {
        $TargetDir = Join-Path (Split-Path -Parent $DefaultRoot) "anakot-agent-v1-fresh"
    } else {
        $TargetDir = $DefaultRoot
    }
} else {
    $TargetDir = [System.IO.Path]::GetFullPath($TargetDir)
}

$RebrandPy = Join-Path $ScriptDir "rebrand.py"
$CustomPatchesPy = Join-Path $ScriptDir "custom_patches.py"

# Formatting helpers
function Write-Header($text) {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host "================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step($text) {
    Write-Host "`n=== $text ===" -ForegroundColor Cyan
}

function Write-Success($text) {
    Write-Host "  [OK] $text" -ForegroundColor Green
}

function Write-Warn($text) {
    Write-Host "  [WARN] $text" -ForegroundColor Yellow
}

function Write-Err($text) {
    Write-Host "  [ERR] $text" -ForegroundColor Red
}

# Find Python executable
function Get-PythonCmd {
    $venvPy = Join-Path $TargetDir ".venv\Scripts\python.exe"
    if (Test-Path $venvPy) { return $venvPy }
    $venvPy2 = Join-Path $TargetDir "venv\Scripts\python.exe"
    if (Test-Path $venvPy2) { return $venvPy2 }
    if (Get-Command "python" -ErrorAction SilentlyContinue) { return "python" }
    if (Get-Command "py" -ErrorAction SilentlyContinue) { return "py -3" }
    throw "Python executable not found. Please install Python 3.10+."
}

# Find uv executable
function Get-UvCmd {
    if (Get-Command "uv" -ErrorAction SilentlyContinue) { return "uv" }
    $localUv = Join-Path $env:USERPROFILE ".cargo\bin\uv.exe"
    if (Test-Path $localUv) { return $localUv }
    $localUv2 = Join-Path $env:LOCALAPPDATA "Programs\uv\uv.exe"
    if (Test-Path $localUv2) { return $localUv2 }
    return $null
}

Write-Header "Anakot Agent -- Setup & Upstream Sync"
Write-Host "  Mode:         $Mode" -ForegroundColor White
Write-Host "  Target:       $TargetDir" -ForegroundColor White
Write-Host "  Upstream:     $UpstreamRepo" -ForegroundColor White
Write-Host "  Fork:         $ForkRepo" -ForegroundColor White

$pythonCmd = Get-PythonCmd
$uvCmd = Get-UvCmd

# ------------------------------------------------------------------------------
# Mode: Fresh Setup
# ------------------------------------------------------------------------------
if ($Mode -eq "Fresh") {
    Write-Step "Step 1: Fresh clone from Anakot upstream"
    if (Test-Path $TargetDir) {
        if (-not $Force) {
            $confirm = Read-Host "Target directory '$TargetDir' already exists. Delete and re-clone? (y/N)"
            if ($confirm -notmatch '^[Yy]') {
                Write-Warn "Aborting fresh clone."
                exit 1
            }
        }
        Remove-Item -Recurse -Force $TargetDir
    }

    Write-Host "Cloning from $UpstreamRepo..."
    & git clone --depth 1 $UpstreamRepo $TargetDir
    if ($LASTEXITCODE -ne 0) { throw "Git clone failed." }

    Push-Location $TargetDir
    try {
        & git remote rename origin upstream
        & git remote add origin $ForkRepo
        Write-Success "Remotes configured: upstream=Anakot, origin=Anakot"
    } finally {
        Pop-Location
    }
}

# ------------------------------------------------------------------------------
# Mode: Sync (Pull latest from upstream Anakot)
# ------------------------------------------------------------------------------
if ($Mode -eq "Sync") {
    Write-Step "Step 1: Fetch and pull latest upstream Anakot"
    Push-Location $TargetDir
    try {
        # Check remotes
        $remotes = & git remote
        if ($remotes -notcontains "upstream") {
            Write-Host "Adding upstream remote: $UpstreamRepo"
            & git remote add upstream $UpstreamRepo
        }

        Write-Host "Fetching upstream main..."
        & git fetch upstream main
        if ($LASTEXITCODE -ne 0) { throw "git fetch upstream failed." }

        $upstreamSha = (& git rev-parse upstream/main).Trim()
        Write-Host "Latest upstream SHA: $upstreamSha"

        # Check if already at or ahead of upstream
        $mergeBase = (& git merge-base HEAD upstream/main).Trim()
        if ($mergeBase -eq $upstreamSha) {
            Write-Success "Already merged latest upstream ($($upstreamSha.Substring(0, 8)))"
        } else {
            Write-Host "Merging upstream/main into current branch..."
            $mergeOutput = & git merge upstream/main --no-edit -m "sync: merge upstream Anakot Agent ($($upstreamSha.Substring(0, 8)))" 2>&1
            if ($LASTEXITCODE -ne 0) {
                Write-Warn "Merge produced conflicts or non-zero exit:"
                $mergeOutput | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
                Write-Warn "Proceeding with rebrand and custom patches to resolve naming differences..."
            } else {
                Write-Success "Upstream merged cleanly."
            }
        }

        # Store last-merged SHA
        $lastMergedFile = Join-Path $TargetDir ".anakot-last-merged"
        Set-Content -Path $lastMergedFile -Value $upstreamSha -Encoding utf8
        Write-Success "Recorded upstream SHA in .anakot-last-merged"
    } finally {
        Pop-Location
    }
}

# ------------------------------------------------------------------------------
# Step 2: Apply Rebrand (anakot -> anakot)
# ------------------------------------------------------------------------------
Write-Step "Step 2: Apply rebrand (anakot -> anakot)"
if (-not (Test-Path $RebrandPy)) {
    throw "rebrand.py not found at $RebrandPy"
}
Write-Host "Running rebrand.py on $TargetDir..."
& $pythonCmd $RebrandPy $TargetDir
if ($LASTEXITCODE -ne 0) {
    Write-Warn "rebrand.py exited with code $LASTEXITCODE"
} else {
    Write-Success "Rebrand applied successfully."
}

# ------------------------------------------------------------------------------
# Step 3: Apply Custom Patches
# ------------------------------------------------------------------------------
Write-Step "Step 3: Apply custom patches"
if (-not (Test-Path $CustomPatchesPy)) {
    throw "custom_patches.py not found at $CustomPatchesPy"
}
Write-Host "Running custom_patches.py on $TargetDir..."
& $pythonCmd $CustomPatchesPy $TargetDir
if ($LASTEXITCODE -ne 0) {
    throw "custom_patches.py failed."
}
Write-Success "Custom patches applied successfully."

# ------------------------------------------------------------------------------
# Step 4: Re-sync Dependencies
# ------------------------------------------------------------------------------
Write-Step "Step 4: Sync dependencies"
Push-Location $TargetDir
try {
    if ($uvCmd) {
        Write-Host "Running uv sync..."
        & $uvCmd sync
        if ($LASTEXITCODE -eq 0) {
            Write-Success "uv sync complete."
        } else {
            Write-Warn "uv sync returned $LASTEXITCODE, attempting editable install..."
            & $pythonCmd -m pip install -e . --no-deps
        }
    } else {
        Write-Host "Running pip install -e ...."
        & $pythonCmd -m pip install -e . --no-deps
        Write-Success "Editable package re-registered."
    }
} finally {
    Pop-Location
}

# ------------------------------------------------------------------------------
# Step 5: Optional Desktop / TUI Build
# ------------------------------------------------------------------------------
if (-not $SkipBuild) {
    $desktopDir = Join-Path $TargetDir "apps\desktop"
    if (Test-Path (Join-Path $desktopDir "package.json")) {
        Write-Step "Step 5: Build Desktop Web UI"
        Push-Location $desktopDir
        try {
            if (Get-Command "npm" -ErrorAction SilentlyContinue) {
                Write-Host "Building desktop static assets..."
                & npm run build 2>&1 | Select-Object -Last 5
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "Desktop Web UI built successfully."
                } else {
                    Write-Warn "Desktop build had warnings or non-zero exit."
                }
            } else {
                Write-Warn "npm not found, skipping desktop build."
            }
        } finally {
            Pop-Location
        }
    }
}

if ($BuildBootstrap) {
    Write-Step "Step 5b: Build Tauri Bootstrap Installer (Anakot-Setup.exe)"
    $bootstrapBat = Join-Path $TargetDir "apps\bootstrap-installer\build-tauri.bat"
    if (Test-Path $bootstrapBat) {
        Write-Host "Compiling Anakot-Setup.exe via build-tauri.bat..."
        & cmd.exe /c $bootstrapBat
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Anakot-Setup.exe compiled successfully."
        } else {
            Write-Warn "build-tauri.bat exited with code $LASTEXITCODE"
        }
    } else {
        Write-Warn "build-tauri.bat not found at $bootstrapBat"
    }
}

# ------------------------------------------------------------------------------
# Step 6: Sanity Checks
# ------------------------------------------------------------------------------
Write-Step "Step 6: Sanity checks"
$checksPassed = 0
$checksFailed = 0

function Run-Check($title, [scriptblock]$action) {
    try {
        $res = & $action
        if ($res -ne $false) {
            Write-Success $title
            $script:checksPassed++
        } else {
            Write-Err "$title (Returned false)"
            $script:checksFailed++
        }
    } catch {
        Write-Err "${title}: $_"
        $script:checksFailed++
    }
}

Run-Check "Import anakot_constants" {
    & $pythonCmd -c "import anakot_constants; print('ok')" 2>$null | Out-Null
    $LASTEXITCODE -eq 0
}

Run-Check "Import anakot_logging" {
    & $pythonCmd -c "import anakot_logging; print('ok')" 2>$null | Out-Null
    $LASTEXITCODE -eq 0
}

Run-Check "Import anakot_state" {
    & $pythonCmd -c "import anakot_state; print('ok')" 2>$null | Out-Null
    $LASTEXITCODE -eq 0
}

Run-Check "No residual anakot_cli imports in active codebase" {
    $checkScript = @"
import os, sys
count = 0
for root, dirs, files in os.walk(r'$TargetDir'):
    dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build'}]
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            try:
                content = open(p, encoding='utf-8', errors='ignore').read()
                if 'from anakot_cli' in content or 'import anakot_cli' in content:
                    if 'rebrand' not in p and 'banner.py' not in p and 'update_cmd' not in p:
                        count += 1
            except: pass
sys.exit(count)
"@
    & $pythonCmd -c $checkScript
    $LASTEXITCODE -eq 0
}

Write-Header "Anakot Agent Setup & Sync Complete!"
Write-Host "  Checks passed: $checksPassed" -ForegroundColor Green
if ($checksFailed -gt 0) {
    Write-Host "  Checks failed: $checksFailed" -ForegroundColor Red
    Write-Warn "Review the errors above."
} else {
    Write-Host "  All checks passed successfully!" -ForegroundColor Green
}
Write-Host ""
Write-Host "  To run Anakot:" -ForegroundColor White
Write-Host "    anakot --help" -ForegroundColor Cyan
Write-Host "    anakot serve" -ForegroundColor Cyan
Write-Host ""
