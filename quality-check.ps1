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
Invoke-Checked { npm --prefix $frontendPath run test:e2e }

Write-Host 'All quality checks passed.' -ForegroundColor Green
