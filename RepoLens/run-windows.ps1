$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker Desktop is not installed or docker is not on PATH.'
}

try {
    docker info | Out-Null
} catch {
    throw 'Docker Desktop is not running. Start Docker Desktop, then run this script again.'
}

$sample = (Resolve-Path "$PSScriptRoot\sample_repo").Path
$env:REPOLENS_SCAN_ROOT = $sample

Write-Host "Starting RepoLens against: $sample"
docker compose up --build -d

Write-Host "Waiting for RepoLens API..."
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $health = Invoke-RestMethod -Uri 'http://localhost:8000/api/health' -TimeoutSec 2
        if ($health.status -eq 'ok') { $ready = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
}

if (-not $ready) {
    docker compose ps
    docker compose logs --tail 100 backend frontend
    throw 'RepoLens did not become healthy. Logs are shown above.'
}

Start-Process 'http://localhost:3000'
Write-Host 'RepoLens is running at http://localhost:3000'
Write-Host 'Enter /repo in the app and click INDEX.'
