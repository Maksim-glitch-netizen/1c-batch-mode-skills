[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Codex', 'Claude', 'Both')]
    [string]$Client,
    [ValidateSet('User', 'Project')]
    [string]$Scope = 'User',
    [string]$ProjectPath
)

$ErrorActionPreference = 'Stop'
Write-Output 'Tests were performed only on Windows. macOS and Linux variants have NOT been tested on their target OS.'
if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
    throw 'Use install.py or the OS-specific shell launcher on macOS/Linux.'
}
$repositoryRoot = [IO.Path]::GetFullPath($PSScriptRoot)
$distributionProfile = [IO.File]::ReadAllText((Join-Path $repositoryRoot 'distribution-profile.json')) | ConvertFrom-Json
if ($distributionProfile.target_os -notin @('universal', 'windows')) {
    throw "This archive targets $($distributionProfile.target_os); use its platform launcher."
}
$pythonCommand = Get-Command python -ErrorAction Stop
& $pythonCommand.Source -B (Join-Path $repositoryRoot 'scripts\validate-package.py')
if ($LASTEXITCODE -ne 0) { throw 'Package validation failed; nothing was installed.' }

if ($Scope -eq 'Project') {
    if ([string]::IsNullOrWhiteSpace($ProjectPath)) { throw '-ProjectPath is required for Project scope.' }
    $basePath = [IO.Path]::GetFullPath($ProjectPath)
    if (-not (Test-Path -LiteralPath $basePath -PathType Container)) {
        throw "Project directory does not exist: $basePath"
    }
} else {
    if (-not [string]::IsNullOrWhiteSpace($ProjectPath)) { throw '-ProjectPath is only valid for Project scope.' }
    $basePath = [Environment]::GetFolderPath('UserProfile')
    if ([string]::IsNullOrWhiteSpace($basePath)) { throw 'User profile directory is unavailable.' }
}

function Get-PayloadFiles {
    param([string]$Directory)
    $items = @(Get-ChildItem -LiteralPath $Directory -Recurse -Force)
    if (@($items | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint }).Count -gt 0) {
        throw "Skill contains a reparse point: $Directory"
    }
    return @($items | Where-Object { -not $_.PSIsContainer } | Sort-Object FullName)
}

function Test-IdenticalSkill {
    param([string]$Source, [string]$Destination)
    if (-not (Test-Path -LiteralPath $Destination -PathType Container)) { return $false }
    $sourceFiles = @(Get-PayloadFiles $Source)
    $destinationFiles = @(Get-PayloadFiles $Destination)
    if ($sourceFiles.Count -ne $destinationFiles.Count) { return $false }
    foreach ($file in $sourceFiles) {
        $relative = $file.FullName.Substring($Source.Length).TrimStart([char[]]@('\', '/'))
        $target = Join-Path $Destination $relative
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { return $false }
        if ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -ne
            (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash) { return $false }
    }
    return $true
}

$clients = if ($Client -eq 'Both') { @('Codex', 'Claude') } else { @($Client) }
$skillNames = @('1c-add-new-object', '1c-configurator-batch-8-3-27')
$plan = New-Object System.Collections.Generic.List[object]

# Preflight every destination before the first write; never replace an existing skill.
foreach ($selectedClient in $clients) {
    $relativeRoot = if ($selectedClient -eq 'Codex') { '.agents\skills' } else { '.claude\skills' }
    foreach ($name in $skillNames) {
        $source = [IO.Path]::GetFullPath((Join-Path $repositoryRoot ('skills\' + $name)))
        $destination = [IO.Path]::GetFullPath((Join-Path (Join-Path $basePath $relativeRoot) $name))
        $identical = $false
        if (Test-Path -LiteralPath $destination) {
            $destinationItem = Get-Item -LiteralPath $destination -Force
            if ($destinationItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Destination is a reparse point; inspect it manually: $destination"
            }
            $identical = Test-IdenticalSkill $source $destination
            if (-not $identical) { throw "Existing skill differs; no files were changed: $destination" }
        }
        $plan.Add([PSCustomObject]@{ Source = $source; Destination = $destination; Identical = $identical })
    }
}

foreach ($item in $plan) {
    if ($item.Identical) {
        Write-Output "Already installed: $($item.Destination)"
        continue
    }
    if ($PSCmdlet.ShouldProcess($item.Destination, 'Install skill without overwriting files')) {
        $parent = Split-Path -Parent $item.Destination
        [void][IO.Directory]::CreateDirectory($parent)
        [void](New-Item -ItemType Directory -Path $item.Destination -ErrorAction Stop)
        foreach ($file in @(Get-PayloadFiles $item.Source)) {
            $relative = $file.FullName.Substring($item.Source.Length).TrimStart([char[]]@('\', '/'))
            $target = Join-Path $item.Destination $relative
            [void][IO.Directory]::CreateDirectory((Split-Path -Parent $target))
            [IO.File]::Copy($file.FullName, $target, $false)
        }
        if (-not (Test-IdenticalSkill $item.Source $item.Destination)) {
            throw "Installed copy failed verification: $($item.Destination). Inspect the new directory."
        }
        Write-Output "Installed: $($item.Destination)"
    }
}
Write-Output 'External scaffolding skills and 1C are installed separately; see docs/dependencies.md.'
