$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$buildRoot = Join-Path $projectRoot 'deployment-build'
$stageRoot = Join-Path $buildRoot 'salovina'
$archivePath = Join-Path $buildRoot 'salovina-cpanel.tar.gz'

$resolvedProject = [System.IO.Path]::GetFullPath($projectRoot)
$resolvedBuild = [System.IO.Path]::GetFullPath($buildRoot)
if (-not $resolvedBuild.StartsWith($resolvedProject + [System.IO.Path]::DirectorySeparatorChar)) {
    throw 'Deployment build directory escaped the project root.'
}

$env:Path = [System.Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path', 'User')
npm --prefix (Join-Path $projectRoot 'frontend') ci
if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' }
npm --prefix (Join-Path $projectRoot 'frontend') run build
if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }

if (Test-Path -LiteralPath $buildRoot) { Remove-Item -LiteralPath $buildRoot -Recurse -Force }
New-Item -ItemType Directory -Path $stageRoot -Force | Out-Null

$rootFiles = @(
    'salovina_wsgi.py', 'deploy-shared-host.sh'
)
foreach ($file in $rootFiles) {
    Copy-Item -LiteralPath (Join-Path $projectRoot $file) -Destination $stageRoot
}

function Copy-DeploymentTree {
    param(
        [string]$Source,
        [string]$Destination,
        [string[]]$ExcludedDirectories,
        [string[]]$ExcludedFiles
    )
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    $arguments = @($Source, $Destination, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP')
    if ($ExcludedDirectories.Count -gt 0) { $arguments += @('/XD') + $ExcludedDirectories }
    if ($ExcludedFiles.Count -gt 0) { $arguments += @('/XF') + $ExcludedFiles }
    & robocopy @arguments | Out-Null
    if ($LASTEXITCODE -gt 7) { throw "Copy failed with robocopy exit code $LASTEXITCODE" }
}

Copy-DeploymentTree `
    -Source (Join-Path $projectRoot 'backend') `
    -Destination (Join-Path $stageRoot 'backend') `
    -ExcludedDirectories @('.venv', '__pycache__', '.pytest_cache', '.ruff_cache', 'staticfiles', 'media', 'test-media') `
    -ExcludedFiles @('*.pyc', '*.pyo', 'db.sqlite3', '.env')
$frontendStage = Join-Path $stageRoot 'frontend'
New-Item -ItemType Directory -Path $frontendStage -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $projectRoot 'frontend\dist') -Destination $frontendStage -Recurse

if (Test-Path -LiteralPath $archivePath) {
    Remove-Item -LiteralPath $archivePath -Force
}
& tar.exe -czf $archivePath -C $stageRoot .
if ($LASTEXITCODE -ne 0) { throw 'Creating the deployment tar.gz failed.' }
Write-Host "Deployment package created: $archivePath" -ForegroundColor Green
