param(
    [string]$RunId = (Get-Date -Format "yyyyMMdd_HHmmss_K").Replace(":", ""),
    [string]$CatalogPath = "",
    [string]$SessionsPath = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runRoot = Join-Path $repoRoot ("integration_runs\" + $RunId)
$logRoot = Join-Path $runRoot "logs"
$resultRoot = Join-Path $runRoot "results"
New-Item -ItemType Directory -Force -Path $logRoot, $resultRoot | Out-Null

$stageRecords = [System.Collections.Generic.List[object]]::new()

function Invoke-AuditStage {
    param(
        [string]$Name,
        [string]$WorkingDirectory,
        [string]$Executable,
        [string[]]$Arguments
    )

    $started = Get-Date
    $logPath = Join-Path $logRoot ($Name + ".log")
    Push-Location $WorkingDirectory
    try {
        & $Executable @Arguments 2>&1 | Tee-Object -FilePath $logPath
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    $ended = Get-Date
    $stageRecords.Add([ordered]@{
        name = $Name
        command = (@($Executable) + $Arguments) -join " "
        working_directory = $WorkingDirectory
        started_at = $started.ToString("o")
        ended_at = $ended.ToString("o")
        elapsed_ms = [math]::Round(($ended - $started).TotalMilliseconds, 3)
        exit_code = $exitCode
        log = $logPath.Substring($repoRoot.Length + 1)
    })
    $stageRecords | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (
        Join-Path $runRoot "stages.json"
    ) -Encoding utf8
    if ($exitCode -ne 0) {
        throw "Audit stage '$Name' failed with exit code $exitCode"
    }
}

function Get-SafeHash {
    param([string]$Path)
    if (-not $Path -or -not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash
}

$manifest = [ordered]@{
    schema_version = "1.0"
    run_id = $RunId
    created_at = (Get-Date).ToString("o")
    repository = $repoRoot
    branch = (git -C $repoRoot branch --show-current)
    integration_commit = (git -C $repoRoot rev-parse HEAD)
    source_commits = [ordered]@{
        main = (git -C $repoRoot rev-parse origin/main)
        testing = (git -C $repoRoot rev-parse origin/testing)
        yxh = (git -C $repoRoot rev-parse origin/yxh)
    }
    worktree_clean = -not [bool](git -C $repoRoot status --porcelain)
    runtime = [ordered]@{
        powershell = $PSVersionTable.PSVersion.ToString()
        uv = (& uv --version)
        python = (& python --version 2>&1)
    }
    model_configuration = [ordered]@{
        shopping_agent_llm_enabled = $env:SHOPPING_AGENT_ENABLE_LLM -in @(
            "1", "true", "TRUE", "yes", "on"
        )
        deepseek_key_configured = [bool]$env:DEEPSEEK_API_KEY
        deepseek_model = $env:DEEPSEEK_MODEL
    }
    inputs = [ordered]@{
        catalog_path = $CatalogPath
        catalog_sha256 = Get-SafeHash $CatalogPath
        sessions_path = $SessionsPath
        sessions_sha256 = Get-SafeHash $SessionsPath
    }
}
$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (
    Join-Path $runRoot "00_manifest.json"
) -Encoding utf8

Invoke-AuditStage "agent_tests" (
    Join-Path $repoRoot "techjam-conversational-search"
) "uv" @("run", "--extra", "deepseek", "--group", "dev", "pytest", "-v")

Invoke-AuditStage "simulator_tests" (
    Join-Path $repoRoot "user-simulator"
) "uv" @("run", "--extra", "dev", "pytest", "-v")

Invoke-AuditStage "simulator_report_tests" (
    Join-Path $repoRoot "user-simulator"
) "uv" @(
    "run", "--extra", "dev", "pytest", "tests/test_reporting.py", "-v"
)

$files = Get-ChildItem -LiteralPath $runRoot -Recurse -File |
    Where-Object { $_.Name -ne "checksums.sha256" }
$checksumLines = foreach ($file in $files) {
    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
    $relative = $file.FullName.Substring($runRoot.Length + 1).Replace("\", "/")
    "$hash  $relative"
}
$checksumLines | Set-Content -LiteralPath (Join-Path $runRoot "checksums.sha256") -Encoding utf8

Write-Output "Audit evidence: $runRoot"
