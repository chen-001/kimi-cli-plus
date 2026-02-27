$ErrorActionPreference = "Stop"

function Install-Uv {
  Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1" | Invoke-Expression
}

if (Get-Command uv -ErrorAction SilentlyContinue) {
  $uvBin = "uv"
} else {
  Install-Uv
  $uvBin = "uv"
}

if (-not (Get-Command $uvBin -ErrorAction SilentlyContinue)) {
  Write-Error "Error: uv not found after installation."
  exit 1
}

# Install kimi-cli-plus from GitHub with user plugins
& $uvBin tool install --python 3.13 --from git+https://github.com/chen-001/kimi-cli-plus.git kimi-cli
