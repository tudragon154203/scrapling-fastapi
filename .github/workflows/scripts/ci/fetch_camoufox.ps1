[CmdletBinding()]
param (
    [Nullable[int]]$MaxRetries,
    [Nullable[int]]$RetryDelaySeconds
)

function Resolve-IntOrDefault {
    param (
        [Parameter(Mandatory = $false)]
        [AllowNull()]
        $Value,
        [Parameter(Mandatory = $true)]
        [int]$Default
    )

    if ($PSBoundParameters.ContainsKey('Value') -and -not [string]::IsNullOrWhiteSpace([string]$Value)) {
        return [int]$Value
    }

    return $Default
}

$effectiveMaxRetries = Resolve-IntOrDefault -Value $MaxRetries -Default (Resolve-IntOrDefault -Value $env:CAMOUFOX_MAX_RETRIES -Default 3)
$effectiveRetryDelay = Resolve-IntOrDefault -Value $RetryDelaySeconds -Default (Resolve-IntOrDefault -Value $env:CAMOUFOX_RETRY_DELAY -Default 10)

for ($attempt = 1; $attempt -le $effectiveMaxRetries; $attempt++) {
    camoufox fetch
    if ($LASTEXITCODE -eq 0) {
        Write-Host "camoufox fetch succeeded on attempt $attempt."
        exit 0
    }

    if ($attempt -eq $effectiveMaxRetries) {
        Write-Error "camoufox fetch failed after $effectiveMaxRetries attempts."
        exit $LASTEXITCODE
    }

    $jitter = Get-Random -Minimum 0 -Maximum 5
    $retryDelaySeconds = $effectiveRetryDelay + $jitter
    Write-Warning "camoufox fetch failed on attempt $attempt. Retrying in $retryDelaySeconds seconds..."
    Start-Sleep -Seconds $retryDelaySeconds
}