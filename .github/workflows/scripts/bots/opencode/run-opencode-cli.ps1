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

try {
    $env:NO_COLOR = '1'
    $env:XDG_CONFIG_HOME = $configHome
    $env:XDG_DATA_HOME = $dataHome

    $promptContent = Get-Content -Path $PromptFile -Raw

    function Invoke-Opencode {
        param([string]$Strategy)

        if ($Strategy -eq 'flag') {
            & $opencode.Source run --model $env:MODEL --prompt $promptContent 1> $StdoutFile 2> $StderrFile
        }
        else {
            & $opencode.Source run --model $env:MODEL -- $promptContent 1> $StdoutFile 2> $StderrFile
        }

        return $LASTEXITCODE
    }

    function Contains-PromptFlagError {
        param([string]$Path)

        if (-not (Test-Path -Path $Path) -or (Get-Item -Path $Path).Length -eq 0) {
            return $false
        }

        $patterns = @(
            '(?i)unrecognized arguments?:\s*--prompt',
            '(?i)no such option:\s*--prompt',
            '(?i)unknown (?:argument|option):\s*--prompt'
        )

        foreach ($pattern in $patterns) {
            if (Select-String -Path $Path -Pattern $pattern -Quiet) {
                return $true
            }
        }

        return $false
    }

    function Should-RetryWithPositional {
        if ($exitCode -eq 0) {
            return $false
        }

        if (Contains-PromptFlagError -Path $StderrFile) {
            return $true
        }

        if (Contains-PromptFlagError -Path $StdoutFile) {
            return $true
        }

        return $false
    }

    $exitCode = Invoke-Opencode -Strategy 'flag'

    if (Should-RetryWithPositional) {
        Clear-Content -Path $StdoutFile
        Clear-Content -Path $StderrFile
        $exitCode = Invoke-Opencode -Strategy 'positional'
    }
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
