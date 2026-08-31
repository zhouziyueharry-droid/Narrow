[CmdletBinding()]
param([string]$CatalogPath = '', [switch]$SkipInstall)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path $PSScriptRoot -Parent
$AgentRoot = Join-Path $RepoRoot 'techjam-conversational-search'
$FrontendRoot = Join-Path $RepoRoot 'demo-frontend'
$TraceRoot = Join-Path $RepoRoot 'trace-visualizer'
$PythonExe = Join-Path $AgentRoot '.venv\Scripts\python.exe'
if (-not $CatalogPath) { $CatalogPath = Join-Path $AgentRoot 'data\catalog.jsonl' }
$CatalogPath = (Resolve-Path -LiteralPath $CatalogPath).Path

if (-not $SkipInstall) {
    Push-Location $AgentRoot
    try {
        & uv sync --extra web --extra ltr --extra deepseek --group dev --cache-dir .uv-cache
        if ($LASTEXITCODE -ne 0) { throw 'Python dependency installation failed.' }
    } finally { Pop-Location }
    foreach ($Directory in @($FrontendRoot, $TraceRoot)) {
        if (-not (Test-Path -LiteralPath (Join-Path $Directory 'node_modules'))) {
            Push-Location $Directory
            try {
                & npm ci --cache .npm-cache --no-audit --no-fund
                if ($LASTEXITCODE -ne 0) { throw 'Frontend dependency installation failed.' }
            } finally { Pop-Location }
        }
    }
}
if (-not (Test-Path -LiteralPath $PythonExe)) { throw 'Missing .venv; run without -SkipInstall first.' }
$NodeExe = (Get-Command node -ErrorAction Stop).Source
$PreviousPythonPath = $env:PYTHONPATH
$Processes = @()
$LogRoot = Join-Path $RepoRoot 'demo_runs\server-logs'
New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null
$Stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
try {
    $env:PYTHONPATH = (Join-Path $AgentRoot 'src') + [IO.Path]::PathSeparator + $AgentRoot
    $Processes += Start-Process -FilePath $PythonExe -ArgumentList @('-m', 'shopping_agent.web', '--catalog', ('"' + $CatalogPath + '"')) -WorkingDirectory $AgentRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $LogRoot "$Stamp-api.out.log") -RedirectStandardError (Join-Path $LogRoot "$Stamp-api.err.log")
    foreach ($Item in @(@{Name='frontend';Root=$FrontendRoot}, @{Name='trace';Root=$TraceRoot})) {
        $Vite = Join-Path $Item.Root 'node_modules\vite\bin\vite.js'
        $Processes += Start-Process -FilePath $NodeExe -ArgumentList @(('"' + $Vite + '"')) -WorkingDirectory $Item.Root -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $LogRoot "$Stamp-$($Item.Name).out.log") -RedirectStandardError (Join-Path $LogRoot "$Stamp-$($Item.Name).err.log")
    }
    Write-Host 'Shopping Copilot: http://127.0.0.1:5173'
    Write-Host 'API: http://127.0.0.1:8000   Trace: http://127.0.0.1:3000'
    Write-Host 'Local provider by default. Press Ctrl+C to stop. Logs:' $LogRoot
    while ($true) {
        foreach ($Process in $Processes) {
            if ($Process.HasExited) { throw "Service exited ($($Process.Id)); check logs in $LogRoot" }
        }
        Start-Sleep -Seconds 1
    }
} finally {
    # Stop only process trees started by this invocation, never unrelated ports.
    foreach ($Process in $Processes) {
        if (-not $Process.HasExited) { & taskkill.exe /PID $Process.Id /T /F | Out-Null }
    }
    $env:PYTHONPATH = $PreviousPythonPath
}
