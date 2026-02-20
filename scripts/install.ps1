# kimi-cli-plus 一键安装脚本 (PowerShell)
# 用法: Invoke-RestMethod https://raw.githubusercontent.com/chen-001/kimi-cli-plus/main/scripts/install.ps1 | Invoke-Expression

$ErrorActionPreference = "Stop"

$PACKAGE_NAME = "kimi-cli-plus"
$PYTHON_VERSION = "3.13"

function Install-Uv {
    Write-Host "Installing uv (Python package manager)..."
    Invoke-RestMethod -Uri "https://astral.sh/uv/install.ps1" | Invoke-Expression
}

# 检查 uv 是否已安装
if (Get-Command uv -ErrorAction SilentlyContinue) {
    $uvBin = "uv"
} else {
    Install-Uv
    # 重新加载环境变量
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "User") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $uvBin = "uv"
}

if (-not (Get-Command $uvBin -ErrorAction SilentlyContinue)) {
    Write-Error "Error: uv not found after installation. Please restart your PowerShell and try again."
    exit 1
}

Write-Host "Installing $PACKAGE_NAME..."
& $uvBin tool install --python $PYTHON_VERSION $PACKAGE_NAME

Write-Host ""
Write-Host "✅ $PACKAGE_NAME installed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Available commands:"
Write-Host "  kcp           - Quick command"
Write-Host "  kimi-plus     - Full command"
Write-Host "  kimi-cli-plus - Alternative command"
Write-Host ""
Write-Host "To verify installation, run: kcp --version"
Write-Host ""
Write-Host "To upgrade: uv tool upgrade $PACKAGE_NAME --no-cache"
Write-Host "To uninstall: uv tool uninstall $PACKAGE_NAME"
