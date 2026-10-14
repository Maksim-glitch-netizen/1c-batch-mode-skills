[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
Write-Output 'Actual release tests: Windows only. macOS and Linux variants have not been tested on their target OS.'
$repositoryRoot = Split-Path -Parent $PSScriptRoot
$pythonCommand = Get-Command python -ErrorAction Stop
$previousNoBytecode = $env:PYTHONDONTWRITEBYTECODE
$previousTestShell = $env:SKILLS_TEST_POWERSHELL
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:SKILLS_TEST_POWERSHELL = (Get-Process -Id $PID).Path
try {
    & $pythonCommand.Source -B (Join-Path $PSScriptRoot 'validate-package.py')
    if ($LASTEXITCODE -ne 0) { throw 'Publication structure/integrity validation failed.' }
    & $pythonCommand.Source -B (Join-Path $PSScriptRoot 'update-manifests.py') --check
    if ($LASTEXITCODE -ne 0) { throw 'Manifest validation failed.' }
    foreach ($name in @('1c-add-new-object', '1c-configurator-batch-8-3-27')) {
        $skillRoot = Join-Path $repositoryRoot ('skills\' + $name)
        & $pythonCommand.Source -B (Join-Path $skillRoot 'scripts\validate-skill.py') --no-tests
        if ($LASTEXITCODE -ne 0) { throw 'Portable skill validator failed.' }
        & (Join-Path $skillRoot 'scripts\validate-skill.ps1') -SkillRoot $skillRoot
    }
    foreach ($script in @(Get-ChildItem -LiteralPath $repositoryRoot -Recurse -Filter '*.ps1' -File)) {
        $parseTokens = $null
        $parseErrors = $null
        [void][System.Management.Automation.Language.Parser]::ParseFile($script.FullName, [ref]$parseTokens, [ref]$parseErrors)
        if ($parseErrors.Count -gt 0) { throw "PowerShell parse errors in $($script.FullName): $parseErrors" }
    }
    & $pythonCommand.Source -B -m unittest discover -s (Join-Path $repositoryRoot 'tests') -p 'test_*.py' -v
    if ($LASTEXITCODE -ne 0) { throw 'Publication tests failed.' }
    Write-Output 'OK: bundle checks, both skill validators, PowerShell parsing, and installation tests passed.'
} finally {
    $env:PYTHONDONTWRITEBYTECODE = $previousNoBytecode
    $env:SKILLS_TEST_POWERSHELL = $previousTestShell
}
