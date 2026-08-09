$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonPath = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'
$env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
$nodePath = (Get-Command node.exe).Source
$backendPath = Join-Path $projectRoot 'backend'
$frontendPath = Join-Path $projectRoot 'frontend'

$backendProcess = Start-Process -FilePath $pythonPath -ArgumentList @('manage.py', 'runserver', '127.0.0.1:8000', '--noreload') -WorkingDirectory $backendPath -WindowStyle Hidden -PassThru
$frontendProcess = Start-Process -FilePath $nodePath -ArgumentList @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173') -WorkingDirectory $frontendPath -WindowStyle Hidden -PassThru

try {
    $apiResponse = $null
    $webResponse = $null
    for ($attempt = 0; $attempt -lt 15; $attempt++) {
        try {
            $apiResponse = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8000/api/health/' -TimeoutSec 2
            $webResponse = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:5173/' -TimeoutSec 2
            break
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    if (-not $apiResponse -or -not $webResponse) {
        throw 'Smoke servers did not become ready.'
    }
    Write-Host "API smoke: $($apiResponse.StatusCode) $($apiResponse.Content)"
    Write-Host "Frontend smoke: $($webResponse.StatusCode), $($webResponse.RawContentLength) bytes"
}
finally {
    $backendChildren = Get-CimInstance Win32_Process -Filter "ParentProcessId=$($backendProcess.Id)" -ErrorAction SilentlyContinue
    $frontendChildren = Get-CimInstance Win32_Process -Filter "ParentProcessId=$($frontendProcess.Id)" -ErrorAction SilentlyContinue
    @($backendChildren.ProcessId) + @($frontendChildren.ProcessId) + @($backendProcess.Id, $frontendProcess.Id) |
        Where-Object { $_ } |
        ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
}
