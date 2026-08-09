$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendRoot = Join-Path $projectRoot 'backend'
$frontendRoot = Join-Path $projectRoot 'frontend'
$pythonPath = Join-Path $backendRoot '.venv\Scripts\python.exe'
$outputLog = Join-Path $env:TEMP 'beauty-production-smoke-output.log'
$errorLog = Join-Path $env:TEMP 'beauty-production-smoke-error.log'

$env:DJANGO_DEBUG = 'false'
$env:DJANGO_SECRET_KEY = 'production-smoke-only-9Xv!3bQ#7Lm@2Rz$5Nk%8Cp&1Ht*6Fw-4Yd+0Sa'
$env:DJANGO_ALLOWED_HOSTS = '127.0.0.1,localhost'
$env:CSRF_TRUSTED_ORIGINS = 'http://127.0.0.1:8010'
$env:CORS_ALLOWED_ORIGINS = 'http://127.0.0.1:8010'
$env:DJANGO_SECURE_SSL_REDIRECT = 'true'
$env:SERVE_MEDIA_FILES = 'true'

& $pythonPath (Join-Path $backendRoot 'manage.py') collectstatic --noinput --verbosity 0
if ($LASTEXITCODE -ne 0) { throw 'collectstatic failed.' }
& $pythonPath (Join-Path $backendRoot 'manage.py') check --deploy
if ($LASTEXITCODE -ne 0) { throw 'Production deployment check failed.' }
$env:DJANGO_SECURE_SSL_REDIRECT = 'false'

$server = Start-Process -FilePath $pythonPath `
    -ArgumentList @('manage.py', 'runserver', '127.0.0.1:8010', '--noreload') `
    -WorkingDirectory $backendRoot -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput $outputLog -RedirectStandardError $errorLog

try {
    $health = $null
    for ($attempt = 0; $attempt -lt 30; $attempt++) {
        try {
            $health = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8010/api/health/' -TimeoutSec 2
            if ($health.StatusCode -eq 200) { break }
        }
        catch { Start-Sleep -Milliseconds 300 }
    }
    if (-not $health -or $health.StatusCode -ne 200) {
        throw (Get-Content -LiteralPath $errorLog -Raw)
    }

    $rootResponse = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8010/' -TimeoutSec 5
    $deepRoute = Invoke-WebRequest -UseBasicParsing 'http://127.0.0.1:8010/salons/demo-rose-gold' -TimeoutSec 5
    $indexHtml = Get-Content -LiteralPath (Join-Path $frontendRoot 'dist\index.html') -Raw
    $assetPath = [regex]::Match($indexHtml, 'src="([^"]+\.js)"').Groups[1].Value
    if (-not $assetPath) { throw 'Built JavaScript asset was not found in index.html.' }
    $asset = Invoke-WebRequest -UseBasicParsing ("http://127.0.0.1:8010$assetPath") -TimeoutSec 5

    Write-Host "Production API health: $($health.StatusCode)" -ForegroundColor Green
    Write-Host "Production React root: $($rootResponse.StatusCode)" -ForegroundColor Green
    Write-Host "Production deep route: $($deepRoute.StatusCode)" -ForegroundColor Green
    Write-Host "Production asset: $($asset.StatusCode) $assetPath" -ForegroundColor Green
}
finally {
    if ($server -and -not $server.HasExited) { Stop-Process -Id $server.Id -Force }
    Remove-Item -LiteralPath $outputLog, $errorLog -Force -ErrorAction SilentlyContinue
}
