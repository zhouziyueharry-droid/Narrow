param(
    [string]$RunId = (Get-Date -Format "yyyyMMdd_HHmmss_K").Replace(":", ""),
    [string]$CatalogPath = "",
    [string]$SessionsPath = "",
    [ValidateSet("smoke", "full")]
    [string]$RunType = "smoke"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runRoot = Join-Path $repoRoot ("integration_runs\" + $RunId)
$logRoot = Join-Path $runRoot "logs"
$resultRoot = Join-Path $runRoot "results"
$comparisonRoot = Join-Path $runRoot "comparisons"
New-Item -ItemType Directory -Force -Path (
    $logRoot, $resultRoot, $comparisonRoot
) | Out-Null

$driveName = ([System.IO.Path]::GetPathRoot($repoRoot)).Substring(0, 1)
$freeSpaceBytes = [int64](Get-PSDrive -Name $driveName).Free
$worktreeClean = -not [bool](git -C $repoRoot status --porcelain)
if ($RunType -eq "full" -and -not $worktreeClean) {
    throw "A full evaluation requires a clean worktree"
}
if ($RunType -eq "full" -and $freeSpaceBytes -lt 2GB) {
    throw "A full evaluation requires at least 2 GiB free space"
}

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
    $exitCode = 1
    $caughtError = $null
    Push-Location $WorkingDirectory
    try {
        & $Executable @Arguments 2>&1 | Tee-Object -FilePath $logPath
        $exitCode = $LASTEXITCODE
    }
    catch {
        $caughtError = $_
        $_ | Out-String | Add-Content -LiteralPath $logPath -Encoding utf8
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
    if ($caughtError -or $exitCode -ne 0) {
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

function Write-AuditChecksums {
    $files = Get-ChildItem -LiteralPath $runRoot -Recurse -File |
        Where-Object { $_.Name -ne "checksums.sha256" }
    $checksumLines = foreach ($file in $files) {
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant()
        $relative = $file.FullName.Substring($runRoot.Length + 1).Replace("\", "/")
        "$hash  $relative"
    }
    $checksumLines | Set-Content -LiteralPath (
        Join-Path $runRoot "checksums.sha256"
    ) -Encoding utf8
}

trap {
    [ordered]@{
        timestamp = (Get-Date).ToString("o")
        status = "failed"
        error_type = $_.Exception.GetType().Name
        error = $_.Exception.Message
    } | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (
        Join-Path $runRoot "failure.json"
    ) -Encoding utf8
    Write-AuditChecksums
    throw
}

$manifest = [ordered]@{
    schema_version = "1.0"
    run_id = $RunId
    run_type = $RunType
    created_at = (Get-Date).ToString("o")
    repository = $repoRoot
    branch = (git -C $repoRoot branch --show-current)
    integration_commit = (git -C $repoRoot rev-parse HEAD)
    source_commits = [ordered]@{
        main = (git -C $repoRoot rev-parse origin/main)
        testing = (git -C $repoRoot rev-parse origin/testing)
        yxh = (git -C $repoRoot rev-parse origin/yxh)
    }
    worktree_clean = $worktreeClean
    free_space_bytes_at_start = $freeSpaceBytes
    runtime = [ordered]@{
        powershell = $PSVersionTable.PSVersion.ToString()
        uv = (& uv --version)
        agent_python = (& uv run --project (
            Join-Path $repoRoot "techjam-conversational-search"
        ) python --version 2>&1 | Out-String).Trim()
        simulator_python = (& uv run --project (
            Join-Path $repoRoot "user-simulator"
        ) python --version 2>&1 | Out-String).Trim()
    }
    model_configuration = [ordered]@{
        evaluation_agent_llm_enabled = $false
        evaluation_user_verbalizer = "template"
        ambient_shopping_agent_llm_enabled = $env:SHOPPING_AGENT_ENABLE_LLM -in @(
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

if ($CatalogPath -and $SessionsPath) {
    $previousLlmSetting = $env:SHOPPING_AGENT_ENABLE_LLM
    $previousPythonPath = $env:PYTHONPATH
    $env:SHOPPING_AGENT_ENABLE_LLM = "false"
    $env:PYTHONPATH = Join-Path $repoRoot "techjam-conversational-search\src"
    try {
        $agentProject = Join-Path $repoRoot "techjam-conversational-search"
        $simulatorProject = Join-Path $repoRoot "user-simulator"
        $techjamJson = Join-Path $resultRoot "techjam.json"
        $techjamMarkdown = Join-Path $resultRoot "techjam.md"
        $realisticJson = Join-Path $resultRoot "realistic.json"
        $realisticMarkdown = Join-Path $resultRoot "realistic.md"
        $techjamSessions = Join-Path $resultRoot "techjam.sessions.jsonl"
        $techjamEvents = Join-Path $logRoot "techjam.events.jsonl"
        $realisticSessions = Join-Path $resultRoot "realistic.sessions.jsonl"
        $realisticEvents = Join-Path $logRoot "realistic.events.jsonl"
        $techjamLimit = if ($RunType -eq "full") { "200" } else { "1" }
        $realisticLimit = if ($RunType -eq "full") { "100" } else { "1" }
        $evaluationLabel = if ($RunType -eq "full") { "full" } else { "smoke" }

        Invoke-AuditStage ("techjam_traditional_" + $evaluationLabel) $repoRoot "uv" @(
            "run", "--project", $agentProject, "--with-editable", $simulatorProject,
            "python", "-m", "user_simulator.cli", "run", "--preset", "techjam",
            "--catalog-path", $CatalogPath, "--sessions-path", $SessionsPath,
            "--agent-class", "shopping_agent.agent:ShoppingAgent", "--limit", $techjamLimit,
            "--output", $techjamJson, "--report-output", $techjamMarkdown,
            "--session-output", $techjamSessions, "--event-output", $techjamEvents
        )
        Invoke-AuditStage ("realistic_traditional_" + $evaluationLabel) $repoRoot "uv" @(
            "run", "--project", $agentProject, "--with-editable", $simulatorProject,
            "python", "-m", "user_simulator.cli", "run", "--preset", "realistic",
            "--catalog-path", $CatalogPath,
            "--agent-class", "shopping_agent.agent:ShoppingAgent", "--limit", $realisticLimit,
            "--output", $realisticJson, "--report-output", $realisticMarkdown,
            "--session-output", $realisticSessions, "--event-output", $realisticEvents
        )
        Invoke-AuditStage "layer_trace_validation" $repoRoot "uv" @(
            "run", "--project", $simulatorProject, "python",
            (Join-Path $repoRoot "scripts\validate_smoke_traces.py"),
            $techjamJson, $realisticJson,
            "--expected-techjam", $techjamLimit,
            "--expected-realistic", $realisticLimit
        )
        Invoke-AuditStage "report_schema_validation" $repoRoot "uv" @(
            "run", "--project", $simulatorProject, "python",
            "C:\Users\Jiang\.codex\skills\shopping-simulator-evaluation\scripts\validate_report.py",
            $techjamJson, $realisticJson
        )
        Invoke-AuditStage "evaluation_analysis" $repoRoot "uv" @(
            "run", "--project", $simulatorProject, "python",
            (Join-Path $repoRoot "scripts\analyze_evaluation_results.py"),
            "--techjam", $techjamJson,
            "--realistic", $realisticJson,
            "--public-set", $SessionsPath,
            "--json-output", (Join-Path $runRoot "analysis.json"),
            "--markdown-output", (Join-Path $runRoot "final_report.md"),
            "--findings-output", (
                Join-Path $comparisonRoot "session_findings.jsonl"
            )
        )
    }
    finally {
        $env:SHOPPING_AGENT_ENABLE_LLM = $previousLlmSetting
        $env:PYTHONPATH = $previousPythonPath
    }
}

Write-AuditChecksums

Write-Output "Audit evidence: $runRoot"
