$ErrorActionPreference = 'Stop'
if (-not (Get-Command pyenv -ErrorAction SilentlyContinue)) {
  Write-Error "pyenv not found in PATH. Ensure pyenv-win is installed and on PATH."
}
if (Test-Path .python-version) {
  Write-Host ".python-version: $(Get-Content .python-version -Raw)"
} else {
  pyenv shell 3.10.8
}
python --version
pip --version