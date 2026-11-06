# Tests for install.ps1's AnakotHome/InstallDir separation guard (#124526).
#
# Run from a PowerShell prompt:
#
#   pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/tests/test-install-ps1-store-guard.ps1
#
# Background: passing -AnakotHome and -InstallDir as the same path (or a
# AnakotHome nested inside -InstallDir) makes the pm tool store land at
# <InstallDir>\tools, INSIDE the checkout. Two failures follow: the
# repository stage's occupied-directory preflight refuses every retry after
# the first run populated the folder ("exists and is not a Anakot git
# checkout"), and `git stash --include-untracked` would sweep the toolchain
# into the stash. The installer now refuses the combination up front, before
# any download, unless ANAKOT_RUNTIME_DIR parks the store elsewhere.
#
# HOW THIS RUNS THE CODE: by executing install.ps1 as a real subprocess with
# crafted -AnakotHome / -InstallDir arguments. -ShowResolvedPaths is a
# side-effect-free early exit that runs AFTER Initialize-ResolvedPaths, so
# the guard executes exactly as during an install. The refusal is a `throw`,
# which under -File exits the child non-zero before the JSON is printed; the
# accepted configurations print the resolved-path JSON with the requested
# paths intact. Nothing here parses install.ps1's source (AGENTS.md bans
# source-reading tests: they pass on broken code and fail on correct
# refactors).

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path))
$installScript = Join-Path $repoRoot "scripts/install.ps1"

if (-not (Test-Path $installScript)) {
    throw "Could not locate install.ps1 at $installScript"
}

$failures = 0

function Assert-True {
    param([bool]$Condition, [Parameter(Mandatory = $true)][string]$Label)
    if (-not $Condition) {
        Write-Host "FAIL: $Label" -ForegroundColor Red
        $script:failures++
    } else {
        Write-Host "OK: $Label" -ForegroundColor Green
    }
}

# Run install.ps1 -ShowResolvedPaths with explicit -AnakotHome/-InstallDir and
# capture (exit code, stdout, stderr). The call operator, not Start-Process:
# `&` inherits this process's environment on every host, and stderr is merged
# so Windows PowerShell 5.1's NativeCommandError records cannot fail the lane.
function Invoke-ResolvedPaths {
    param([string[]]$ExtraArgs = @())

    $psExe = (Get-Process -Id $PID).Path
    $outFile = [System.IO.Path]::GetTempFileName()
    $savedRuntimeDir = [Environment]::GetEnvironmentVariable('ANAKOT_RUNTIME_DIR')
    $savedAnakotHome = [Environment]::GetEnvironmentVariable('ANAKOT_HOME')
    try {
        if ($null -eq $savedRuntimeDir) {
            Remove-Item Env:ANAKOT_RUNTIME_DIR -ErrorAction SilentlyContinue
        } else {
            $env:ANAKOT_RUNTIME_DIR = $savedRuntimeDir
        }
        if ($null -eq $savedAnakotHome) {
            Remove-Item Env:ANAKOT_HOME -ErrorAction SilentlyContinue
        } else {
            $env:ANAKOT_HOME = $savedAnakotHome
        }
        $callArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $installScript) + $ExtraArgs + @('-ShowResolvedPaths')
        $prevEAP = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $global:LASTEXITCODE = 0
        try {
            & $psExe @callArgs *> $outFile
        } finally {
            $ErrorActionPreference = $prevEAP
        }
        $exitCode = $LASTEXITCODE
        $raw = @(Get-Content -LiteralPath $outFile -ErrorAction SilentlyContinue)
        $stdout = ($raw | Where-Object { $_ -notlike '`[anakot`]*' }) -join "`n"
        $stderr = ($raw | Where-Object { $_ -like '`[anakot`]*' -or $_ -match 'AnakotHome|install directory|tool store' }) -join "`n"
        return @{ ExitCode = $exitCode; Stdout = $stdout; All = ($raw -join "`n") }
    } finally {
        if ($null -eq $savedRuntimeDir) {
            Remove-Item Env:ANAKOT_RUNTIME_DIR -ErrorAction SilentlyContinue
        } else {
            $env:ANAKOT_RUNTIME_DIR = $savedRuntimeDir
        }
        if ($null -eq $savedAnakotHome) {
            Remove-Item Env:ANAKOT_HOME -ErrorAction SilentlyContinue
        } else {
            $env:ANAKOT_HOME = $savedAnakotHome
        }
        Remove-Item -LiteralPath $outFile -Force -ErrorAction SilentlyContinue
    }
}

$base = Join-Path ([System.IO.Path]::GetTempPath()) ("anakot-store-guard-" + [guid]::NewGuid())
$home1 = Join-Path $base 'home1'
$dir1 = Join-Path $base 'checkout1'
$insideHome = Join-Path $base 'checkout2'      # AnakotHome nested inside InstallDir
$insideDir = Join-Path $base 'checkout2'       # the InstallDir that contains it

try {
    # 1. Same path for both: refused, before any download.
    $r = Invoke-ResolvedPaths @('-AnakotHome', $home1, '-InstallDir', $home1)
    Assert-True ($r.ExitCode -ne 0) 'same AnakotHome and InstallDir is refused (non-zero exit)'
    Assert-True ($r.All -match 'tool store would land inside the checkout') 'refusal names the tool-store cause'

    # 2. AnakotHome nested inside InstallDir: refused for the same reason.
    $r = Invoke-ResolvedPaths @('-AnakotHome', $insideHome, '-InstallDir', $insideDir)
    Assert-True ($r.ExitCode -ne 0) 'AnakotHome inside InstallDir is refused (non-zero exit)'

    # 3. Distinct paths: accepted, and the caller's paths survive verbatim.
    $r = Invoke-ResolvedPaths @('-AnakotHome', $home1, '-InstallDir', $dir1)
    Assert-True ($r.ExitCode -eq 0) "distinct paths are accepted (exit $($r.ExitCode))"
    $paths = $null
    try { $paths = $r.Stdout | ConvertFrom-Json } catch { $paths = $null }
    Assert-True ($null -ne $paths) 'accepted run prints the resolved-path JSON'
    if ($paths) {
        Assert-True ("$($paths.anakot_home)" -eq $home1) 'anakot_home echoes the requested -AnakotHome'
        Assert-True ("$($paths.install_dir)" -eq $dir1) 'install_dir echoes the requested -InstallDir'
    }

    # 4. ANAKOT_RUNTIME_DIR outside the checkout lifts the refusal: the store
    #    no longer lands inside InstallDir, so the configuration is legitimate.
    $storeElsewhere = Join-Path $base 'store'
    $saved = $env:ANAKOT_RUNTIME_DIR
    try {
        $env:ANAKOT_RUNTIME_DIR = $storeElsewhere
        $r = Invoke-ResolvedPaths @('-AnakotHome', $home1, '-InstallDir', $home1)
        Assert-True ($r.ExitCode -eq 0) "ANAKOT_RUNTIME_DIR outside lifts the refusal (exit $($r.ExitCode))"
    } finally {
        if ($null -eq $saved) {
            Remove-Item Env:ANAKOT_RUNTIME_DIR -ErrorAction SilentlyContinue
        } else {
            $env:ANAKOT_RUNTIME_DIR = $saved
        }
    }

    # 5. Default derivation never trips the guard: InstallDir defaults to
    #    <AnakotHome>\anakot-agent, which is a child, not a parent.
    $r = Invoke-ResolvedPaths @('-AnakotHome', $home1)
    Assert-True ($r.ExitCode -eq 0) "default -InstallDir under -AnakotHome stays accepted (exit $($r.ExitCode))"
    $paths = $null
    try { $paths = $r.Stdout | ConvertFrom-Json } catch { $paths = $null }
    if ($paths) {
        Assert-True ("$($paths.install_dir)" -eq (Join-Path $home1 'anakot-agent')) 'default install_dir derives under anakot_home'
    }
} finally {
    Remove-Item -LiteralPath $base -Recurse -Force -ErrorAction SilentlyContinue
}

if ($failures -gt 0) {
    Write-Host "$failures assertion(s) failed." -ForegroundColor Red
    exit 1
}
Write-Host 'AnakotHome/InstallDir separation guard tests passed.' -ForegroundColor Green
exit 0
