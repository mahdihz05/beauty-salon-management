$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $projectRoot 'backend'
$frontendPath = Join-Path $projectRoot 'frontend'
$pythonPath = Join-Path $backendPath '.venv\Scripts\python.exe'
$backendPort = 8000..8010 | Where-Object {
    -not (Get-NetTCPConnection -State Listen -LocalPort $_ -ErrorAction SilentlyContinue)
} | Select-Object -First 1
$frontendPort = 5173..5180 | Where-Object {
    -not (Get-NetTCPConnection -State Listen -LocalPort $_ -ErrorAction SilentlyContinue)
} | Select-Object -First 1

if (-not $backendPort -or -not $frontendPort) {
    throw 'No free development port was found in ranges 8000-8010 and 5173-5180.'
}

& $pythonPath (Join-Path $backendPath 'manage.py') migrate --noinput
& $pythonPath (Join-Path $backendPath 'manage.py') seed_demo
& $pythonPath (Join-Path $backendPath 'manage.py') seed_showcase

$backendJob = Start-Job -ScriptBlock {
    param($python, $backend, $port)
    Set-Location -LiteralPath $backend
    & $python manage.py runserver "127.0.0.1:$port"
} -ArgumentList $pythonPath, $backendPath, $backendPort

try {
    $env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
    $env:VITE_DEV_API_PROXY = "http://127.0.0.1:$backendPort"
    Remove-Item Env:VITE_API_URL -ErrorAction SilentlyContinue
    Write-Host "Backend: http://127.0.0.1:$backendPort/api/docs/" -ForegroundColor DarkYellow
    Write-Host "Frontend: http://127.0.0.1:$frontendPort/" -ForegroundColor DarkYellow
    npm --prefix $frontendPath run dev -- --host 127.0.0.1 --port $frontendPort
}
finally {
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -Force -ErrorAction SilentlyContinue
}
