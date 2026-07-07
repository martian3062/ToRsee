$ErrorActionPreference = "Stop"

$cacheRoot = "E:\cache"
$projectCache = Join-Path $cacheRoot "ToRsy"

$paths = @(
  $cacheRoot,
  $projectCache,
  (Join-Path $projectCache "uv"),
  (Join-Path $projectCache "python"),
  (Join-Path $projectCache "pip"),
  (Join-Path $projectCache "npm"),
  (Join-Path $projectCache "hf"),
  (Join-Path $projectCache "torch"),
  (Join-Path $projectCache "transformers"),
  (Join-Path $projectCache "playwright"),
  (Join-Path $projectCache ".venv")
)

foreach ($path in $paths) {
  New-Item -ItemType Directory -Force -Path $path | Out-Null
}

$env:UV_PROJECT_ENVIRONMENT = Join-Path $projectCache ".venv"
$env:UV_CACHE_DIR = Join-Path $projectCache "uv"
$env:UV_PYTHON = "3.10"
$env:UV_PYTHON_INSTALL_DIR = Join-Path $projectCache "python"
$env:UV_MANAGED_PYTHON = "1"
$env:PIP_CACHE_DIR = Join-Path $projectCache "pip"
$env:NPM_CONFIG_CACHE = Join-Path $projectCache "npm"
$env:HF_HOME = Join-Path $projectCache "hf"
$env:HUGGINGFACE_HUB_CACHE = Join-Path $projectCache "hf\hub"
$env:TRANSFORMERS_CACHE = Join-Path $projectCache "transformers"
$env:TORCH_HOME = Join-Path $projectCache "torch"
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $projectCache "playwright"
$env:PYTHONPYCACHEPREFIX = Join-Path $projectCache "pycache"

Write-Host "ToRsy cache root set to $projectCache"
Write-Host "Python venv: $env:UV_PROJECT_ENVIRONMENT"
