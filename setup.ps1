$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $projectRoot 'backend'
$frontendPath = Join-Path $projectRoot 'frontend'
$pythonPath = Join-Path $backendPath '.venv\Scripts\python.exe'

function Invoke-Checked {
    param([scriptblock]$Command)
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE" }
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    python -m venv (Join-Path $backendPath '.venv')
}

Invoke-Checked { & $pythonPath -m pip install --disable-pip-version-check -r (Join-Path $backendPath 'requirements.txt') }
Invoke-Checked { & $pythonPath (Join-Path $backendPath 'manage.py') migrate --noinput }
Invoke-Checked { & $pythonPath (Join-Path $backendPath 'manage.py') seed_demo }
Invoke-Checked { & $pythonPath (Join-Path $backendPath 'manage.py') seed_showcase }

$env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
Invoke-Checked { npm --prefix $frontendPath install }

Write-Host 'راه‌اندازی پروژه با موفقیت انجام شد.' -ForegroundColor Green
