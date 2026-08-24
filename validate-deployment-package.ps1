$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot 'deployment-build'))
$validationRoot = [System.IO.Path]::GetFullPath((Join-Path $buildRoot 'package-validation'))
$archivePath = Join-Path $buildRoot 'salovina-cpanel.tar.gz'
$pythonPath = Join-Path $projectRoot 'backend\.venv\Scripts\python.exe'

if (-not $validationRoot.StartsWith($buildRoot + [System.IO.Path]::DirectorySeparatorChar)) {
    throw 'Validation directory escaped deployment-build.'
}
if (-not (Test-Path -LiteralPath $archivePath)) { throw 'Deployment tar.gz does not exist.' }
if (Test-Path -LiteralPath $validationRoot) {
    Remove-Item -LiteralPath $validationRoot -Recurse -Force
}

try {
    New-Item -ItemType Directory -Path $validationRoot -Force | Out-Null
    & tar.exe -xzf $archivePath -C $validationRoot
    if ($LASTEXITCODE -ne 0) { throw 'Extracting the deployment tar.gz failed.' }
    $appRoot = $validationRoot
    $dataRoot = Join-Path $appRoot 'data'
    New-Item -ItemType Directory -Path $dataRoot -Force | Out-Null

    $requiredFiles = @(
        'salovina_wsgi.py',
        'backend\requirements-production.txt',
        'frontend\dist\index.html',
        'deploy-shared-host.sh'
    )
    foreach ($relativePath in $requiredFiles) {
        if (-not (Test-Path -LiteralPath (Join-Path $appRoot $relativePath))) {
            throw "Packaged file is missing: $relativePath"
        }
    }
    if (Test-Path -LiteralPath (Join-Path $appRoot 'backend\.env')) {
        throw 'A sensitive backend/.env file was included in the package.'
    }
    if (Test-Path -LiteralPath (Join-Path $appRoot 'backend\db.sqlite3')) {
        throw 'A local database was included in the package.'
    }

    $env:DJANGO_DEBUG = 'false'
    $env:DJANGO_SECRET_KEY = 'package-validation-only-9Xv!3bQ#7Lm@2Rz$5Nk%8Cp&1Ht*6Fw-4Yd+0Sa'
    $env:DJANGO_ALLOWED_HOSTS = 'validation.local'
    $env:CSRF_TRUSTED_ORIGINS = 'https://validation.local'
    $env:CORS_ALLOWED_ORIGINS = 'https://validation.local'
    $env:DJANGO_SECURE_SSL_REDIRECT = 'false'
    $env:SERVE_MEDIA_FILES = 'true'
    $env:SQLITE_PATH = Join-Path $dataRoot 'db.sqlite3'
    $env:MEDIA_ROOT = Join-Path $dataRoot 'media'

    $managePath = Join-Path $appRoot 'backend\manage.py'
    & $pythonPath $managePath migrate --noinput --verbosity 0
    if ($LASTEXITCODE -ne 0) { throw 'Packaged migrations failed.' }
    & $pythonPath $managePath collectstatic --noinput --verbosity 0
    if ($LASTEXITCODE -ne 0) { throw 'Packaged collectstatic failed.' }
    & $pythonPath $managePath check
    if ($LASTEXITCODE -ne 0) { throw 'Packaged Django check failed.' }

    $indexPath = Join-Path $appRoot 'frontend\dist\index.html'
    $validationCode = @"
import re
from pathlib import Path
from django.test import Client
client = Client(HTTP_HOST="validation.local")
index = Path(r"$indexPath").read_text(encoding="utf-8")
asset = re.search(r'src="([^"]+\.js)"', index).group(1)
statuses = [
    client.get("/api/health/").status_code,
    client.get("/").status_code,
    client.get("/salons/demo-rose-gold").status_code,
    client.get(asset).status_code,
]
print("Packaged production responses:", statuses)
assert statuses == [200, 200, 200, 200]
"@
    $encodedCode = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($validationCode))
    $shellCommand = "import base64;exec(base64.b64decode('$encodedCode'))"
    & $pythonPath $managePath shell -c $shellCommand
    if ($LASTEXITCODE -ne 0) { throw 'Packaged runtime validation failed.' }

    $sizeMb = [math]::Round((Get-Item -LiteralPath $archivePath).Length / 1MB, 2)
    Write-Host "Deployment tar.gz validation passed ($sizeMb MB)." -ForegroundColor Green
}
finally {
    if (Test-Path -LiteralPath $validationRoot) {
        Remove-Item -LiteralPath $validationRoot -Recurse -Force
    }
}
