$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $projectRoot 'backend'
$frontendPath = Join-Path $projectRoot 'frontend'
$pythonPath = Join-Path $backendPath '.venv\Scripts\python.exe'
$ruffPath = Join-Path $backendPath '.venv\Scripts\ruff.exe'

function Invoke-Checked {
    param([scriptblock]$Command)
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "Command failed with exit code $LASTEXITCODE" }
}

Invoke-Checked { & $ruffPath check $backendPath }
Invoke-Checked { & $pythonPath -m pytest $backendPath }
Invoke-Checked { & $pythonPath (Join-Path $backendPath 'manage.py') check }
Invoke-Checked { & $pythonPath (Join-Path $backendPath 'manage.py') makemigrations --check --dry-run }
Invoke-Checked { & $pythonPath (Join-Path $backendPath 'manage.py') spectacular --file (Join-Path $backendPath 'api-schema.yml') --validate }

$env:DJANGO_DEBUG = 'false'
$env:DJANGO_SECRET_KEY = 'quality-check-only-9Xv!3bQ#7Lm@2Rz$5Nk%8Cp&1Ht*6Fw'
Invoke-Checked { & $pythonPath (Join-Path $backendPath 'manage.py') check --deploy }

$env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
Invoke-Checked { npm --prefix $frontendPath run lint }
Invoke-Checked { npm --prefix $frontendPath run typecheck }
Invoke-Checked { npm --prefix $frontendPath run test }
Invoke-Checked { npm --prefix $frontendPath run format:check }
Invoke-Checked { npm --prefix $frontendPath run build }
Invoke-Checked { npm --prefix $frontendPath audit --omit=dev }
$env:DJANGO_DEBUG = 'true'
$e2eBackendPort = 8000..8010 | Where-Object {
    -not (Get-NetTCPConnection -State Listen -LocalPort $_ -ErrorAction SilentlyContinue)
} | Select-Object -First 1
$e2eFrontendPort = 5173..5190 | Where-Object {
    -not (Get-NetTCPConnection -State Listen -LocalPort $_ -ErrorAction SilentlyContinue)
} | Select-Object -First 1
if (-not $e2eBackendPort -or -not $e2eFrontendPort) {
    throw 'No free ports are available for the E2E servers.'
}
$env:E2E_BACKEND_PORT = [string]$e2eBackendPort
$env:E2E_FRONTEND_PORT = [string]$e2eFrontendPort
Invoke-Checked { npm --prefix $frontendPath run test:e2e }

Write-Host 'All quality checks passed.' -ForegroundColor Green
