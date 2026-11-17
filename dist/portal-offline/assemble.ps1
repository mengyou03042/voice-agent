# Copyright (c) Microsoft. All rights reserved.
# Verify and reassemble the split offline Voice Agent portal delivery archive on Windows / PowerShell.
[CmdletBinding()]
param(
    [string]$OutputPath = "",
    [switch]$Extract,
    [string]$ExtractTo = ""
)

$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Version = "d112175c0dcb"
$ArchiveName = "voice-agent-portal-delivery-$Version.zip"

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $Here $ArchiveName
}
if (-not [string]::IsNullOrWhiteSpace($ExtractTo)) {
    $Extract = $true
} elseif ($Extract) {
    $ExtractTo = $Here
}

$SumsFile = Join-Path $Here "SHA256SUMS"
$ArchiveShaFile = Join-Path $Here "$ArchiveName.sha256"

if (-not (Test-Path -LiteralPath $SumsFile)) {
    throw "Missing $SumsFile"
}
if (-not (Test-Path -LiteralPath $ArchiveShaFile)) {
    throw "Missing $ArchiveShaFile"
}

Write-Host "==> Verifying split parts against SHA256SUMS..."
$PartPaths = New-Object System.Collections.Generic.List[string]
foreach ($RawLine in Get-Content -LiteralPath $SumsFile) {
    $Line = $RawLine.Trim()
    if ([string]::IsNullOrWhiteSpace($Line)) { continue }
    $Tokens = $Line -split "\s+", 2
    if ($Tokens.Count -lt 2) {
        throw "Malformed line in SHA256SUMS: $Line"
    }
    $Expected = $Tokens[0].ToLowerInvariant()
    $RelPath = $Tokens[1].Trim()
    $FullPath = Join-Path $Here ($RelPath -replace "/", [System.IO.Path]::DirectorySeparatorChar)
    if (-not (Test-Path -LiteralPath $FullPath)) {
        throw "Missing part file: $FullPath"
    }
    $Actual = (Get-FileHash -LiteralPath $FullPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Actual -ne $Expected) {
        throw "Checksum mismatch for ${RelPath}: expected $Expected, got $Actual"
    }
    Write-Host "  OK  $RelPath"
    $PartPaths.Add($FullPath)
}

if ($PartPaths.Count -eq 0) {
    throw "No part entries found in SHA256SUMS"
}

$OutDir = Split-Path -Parent ([System.IO.Path]::GetFullPath($OutputPath))
if (-not (Test-Path -LiteralPath $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}

$TmpZip = "$OutputPath.tmp.$PID"
Write-Host ("==> Joining {0} parts into {1}..." -f $PartPaths.Count, $OutputPath)
try {
    $OutStream = [System.IO.File]::Open($TmpZip, [System.IO.FileMode]::Create, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    try {
        foreach ($Part in $PartPaths) {
            $InStream = [System.IO.File]::OpenRead($Part)
            try {
                $InStream.CopyTo($OutStream, 4194304)
            } finally {
                $InStream.Dispose()
            }
        }
    } finally {
        $OutStream.Dispose()
    }

    $ExpectedArchiveSha = ((Get-Content -LiteralPath $ArchiveShaFile -TotalCount 1).Trim() -split "\s+")[0].ToLowerInvariant()
    $ActualArchiveSha = (Get-FileHash -LiteralPath $TmpZip -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($ActualArchiveSha -ne $ExpectedArchiveSha) {
        throw "Archive checksum mismatch: expected $ExpectedArchiveSha, got $ActualArchiveSha"
    }

    Move-Item -LiteralPath $TmpZip -Destination $OutputPath -Force
    Write-Host "  OK  $OutputPath (sha256: $ActualArchiveSha)"
} finally {
    if (Test-Path -LiteralPath $TmpZip) {
        Remove-Item -LiteralPath $TmpZip -Force -ErrorAction SilentlyContinue
    }
}

if ($Extract) {
    if (-not (Test-Path -LiteralPath $ExtractTo)) {
        New-Item -ItemType Directory -Path $ExtractTo -Force | Out-Null
    }
    Write-Host "==> Extracting $OutputPath into $ExtractTo..."
    Expand-Archive -LiteralPath $OutputPath -DestinationPath $ExtractTo -Force
    $ReadyReadme = Join-Path (Join-Path $ExtractTo "voice-agent-portal-delivery-$Version") "README.md"
    Write-Host "==> Ready: $ReadyReadme"
} else {
    Write-Host "==> Done. Run .\assemble.cmd -Extract (or Expand-Archive) to unpack."
}
