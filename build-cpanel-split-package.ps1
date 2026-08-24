$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildRoot = Join-Path $projectRoot 'deployment-build\split'
$frontendStage = Join-Path $buildRoot 'frontend'
$backendStage = Join-Path $buildRoot 'backend'
$frontendArchive = Join-Path $projectRoot 'artifacts\salovina-frontend.tar.gz'
$backendArchive = Join-Path $projectRoot 'artifacts\salovina-backend.tar.gz'

$resolvedProject = [System.IO.Path]::GetFullPath($projectRoot)
$resolvedBuild = [System.IO.Path]::GetFullPath($buildRoot)
if (-not $resolvedBuild.StartsWith($resolvedProject + [System.IO.Path]::DirectorySeparatorChar)) {
    throw 'Deployment build directory escaped the project root.'
}

$env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
$env:VITE_API_URL = 'https://api.saloniva.ir/api'
npm.cmd --prefix (Join-Path $projectRoot 'frontend') ci
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
npm.cmd --prefix (Join-Path $projectRoot 'frontend') run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }

if (Test-Path -LiteralPath $buildRoot) {
    Remove-Item -LiteralPath $buildRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $frontendStage -Force | Out-Null
New-Item -ItemType Directory -Path $backendStage -Force | Out-Null
New-Item -ItemType Directory -Path (Split-Path -Parent $frontendArchive) -Force | Out-Null

Copy-Item -LiteralPath (Join-Path $projectRoot 'deployment\cpanel\frontend\server.js') -Destination $frontendStage
Copy-Item -LiteralPath (Join-Path $projectRoot 'deployment\cpanel\frontend\package.json') -Destination $frontendStage
Copy-Item -LiteralPath (Join-Path $projectRoot 'frontend\dist') -Destination (Join-Path $frontendStage 'frontend') -Recurse

Copy-Item -LiteralPath (Join-Path $projectRoot 'deployment\cpanel\backend\app.py') -Destination $backendStage
Copy-Item -LiteralPath (Join-Path $projectRoot 'deployment\cpanel\backend\deploy.sh') -Destination $backendStage
& robocopy (Join-Path $projectRoot 'backend') (Join-Path $backendStage 'backend') /E /NFL /NDL /NJH /NJS /NP /XD .venv __pycache__ .pytest_cache .ruff_cache staticfiles media test-media /XF *.pyc *.pyo db.sqlite3 .env | Out-Null
if ($LASTEXITCODE -gt 7) { throw "Backend copy failed with robocopy exit code $LASTEXITCODE" }

foreach ($archive in @($frontendArchive, $backendArchive)) {
    if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
}
& tar.exe -czf $frontendArchive -C $frontendStage .
if ($LASTEXITCODE -ne 0) { throw 'Creating frontend tar.gz failed.' }
& tar.exe -czf $backendArchive -C $backendStage .
if ($LASTEXITCODE -ne 0) { throw 'Creating backend tar.gz failed.' }

Write-Host "Frontend package: $frontendArchive" -ForegroundColor Green
Write-Host "Backend package:  $backendArchive" -ForegroundColor Green
