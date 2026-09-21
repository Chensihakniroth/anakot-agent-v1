# Wrapper for scripts/rebrand/anakot-setup.ps1
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$TargetScript = Join-Path $ScriptDir "rebrand\anakot-setup.ps1"
& $TargetScript @args
