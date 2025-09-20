param(
    [Parameter(Mandatory = $true)][string]$PromptFile,
    [Parameter(Mandatory = $true)][string]$StdoutFile,
    [Parameter(Mandatory = $true)][string]$StderrFile,
    [Parameter(Mandatory = $true)][string]$OutputsFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-OutputsLine {
    param([string]$Line)
    Add-Content -Path $OutputsFile -Value $Line
}

if ([string]::IsNullOrWhiteSpace($env:MODEL)) {
    [Console]::Error.WriteLine('::error::MODEL environment variable is not set.')
    exit 1
}

$stdoutDir = Split-Path -Path $StdoutFile -Parent
if ($stdoutDir) {
    New-Item -ItemType Directory -Path $stdoutDir -Force | Out-Null
}
$stderrDir = Split-Path -Path $StderrFile -Parent
if ($stderrDir) {
    New-Item -ItemType Directory -Path $stderrDir -Force | Out-Null
}
$outputsDir = Split-Path -Path $OutputsFile -Parent
if ($outputsDir) {
    New-Item -ItemType Directory -Path $outputsDir -Force | Out-Null
}

New-Item -ItemType File -Path $StdoutFile -Force | Out-Null
New-Item -ItemType File -Path $StderrFile -Force | Out-Null
Remove-Item -Path $OutputsFile -Force -ErrorAction SilentlyContinue
New-Item -ItemType File -Path $OutputsFile -Force | Out-Null

$opencode = Get-Command 'opencode' -ErrorAction SilentlyContinue
if (-not $opencode) {
    $message = 'opencode CLI is not available on the PATH.'
    [Console]::Error.WriteLine("::error::$message")
    Add-Content -Path $StderrFile -Value $message
    Write-OutputsLine 'exit_code=127'
    Write-OutputsLine ("stdout_file=$StdoutFile")
    Write-OutputsLine ("stderr_file=$StderrFile")
    exit 0
}

if (-not (Test-Path -Path $PromptFile) -or (Get-Item -Path $PromptFile).Length -eq 0) {
    [Console]::Error.WriteLine('::error::Prompt content is empty.')
    Write-OutputsLine 'exit_code=1'
    Write-OutputsLine ("stdout_file=$StdoutFile")
    Write-OutputsLine ("stderr_file=$StderrFile")
    exit 0
}

if (-not $env:RUNNER_TEMP) {
    $tempRoot = Join-Path -Path ([System.IO.Path]::GetTempPath()) -ChildPath ([guid]::NewGuid().ToString())
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
}
else {
    $tempRoot = $env:RUNNER_TEMP
}

$configRoot = $tempRoot
$configHome = Join-Path -Path $configRoot -ChildPath 'opencode-config'
$dataHome = Join-Path -Path $configRoot -ChildPath 'opencode-data'
New-Item -ItemType Directory -Path $configHome -Force | Out-Null
New-Item -ItemType Directory -Path $dataHome -Force | Out-Null

$previousEnv = @{
    'NO_COLOR' = $env:NO_COLOR
    'XDG_CONFIG_HOME' = $env:XDG_CONFIG_HOME
    'XDG_DATA_HOME' = $env:XDG_DATA_HOME
}

[int]$exitCode = 0

try {
    $env:NO_COLOR = '1'
    $env:XDG_CONFIG_HOME = $configHome
    $env:XDG_DATA_HOME = $dataHome

    $promptContent = Get-Content -Path $PromptFile -Raw
    # Supply the prompt as the final positional argument in accordance with the CLI docs.
    & $opencode.Source run --model $env:MODEL $promptContent 1> $StdoutFile 2> $StderrFile
    $exitCode = $LASTEXITCODE
}
finally {
    if ($previousEnv['NO_COLOR']) {
        $env:NO_COLOR = $previousEnv['NO_COLOR']
    }
    else {
        Remove-Item Env:NO_COLOR -ErrorAction SilentlyContinue
    }

    if ($previousEnv['XDG_CONFIG_HOME']) {
        $env:XDG_CONFIG_HOME = $previousEnv['XDG_CONFIG_HOME']
    }
    else {
        Remove-Item Env:XDG_CONFIG_HOME -ErrorAction SilentlyContinue
    }

    if ($previousEnv['XDG_DATA_HOME']) {
        $env:XDG_DATA_HOME = $previousEnv['XDG_DATA_HOME']
    }
    else {
        Remove-Item Env:XDG_DATA_HOME -ErrorAction SilentlyContinue
    }
}

Write-OutputsLine ("stdout_file=$StdoutFile")
Write-OutputsLine ("stderr_file=$StderrFile")
Write-OutputsLine ("exit_code=$exitCode")
Write-OutputsLine ("model=$($env:MODEL)")

exit 0
