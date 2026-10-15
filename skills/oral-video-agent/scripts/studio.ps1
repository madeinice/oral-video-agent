[CmdletBinding()]
param(
    [ValidateSet('Start','Serve','Stop','Render','Doctor')][string]$Action = 'Start',
    [string]$ProjectPath = '',
    [string]$RuntimeConfig = '',
    [string]$OutputPath = '',
    [int]$Port = 0,
    [switch]$NoOpen
)
$ErrorActionPreference = 'Stop'
if (-not $ProjectPath) { $ProjectPath = $PSScriptRoot }
$ProjectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
if (-not (Test-Path -LiteralPath (Join-Path $ProjectPath 'src\index.ts'))) {
    throw 'Pass the generated outputs/editor directory as ProjectPath.'
}
$taskRoot = Split-Path -Parent (Split-Path -Parent $ProjectPath)
$runtimeWork = Join-Path $taskRoot 'work\studio'
New-Item -ItemType Directory -Force -Path $runtimeWork | Out-Null
$stateFile = Join-Path $runtimeWork 'studio-state.json'
if (-not $RuntimeConfig) { $RuntimeConfig = Join-Path $ProjectPath 'runtime.local.json' }
$settings = @{}
if (Test-Path -LiteralPath $RuntimeConfig) {
    $settings = Get-Content -Raw -LiteralPath $RuntimeConfig | ConvertFrom-Json
}
if ($Port -eq 0) { $Port = if ($settings.port) { [int]$settings.port } else { 3039 } }
if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Use a port from 1024 to 65535.' }
$url = "http://127.0.0.1:$Port/"

function Read-State {
    if (Test-Path -LiteralPath $stateFile) { return Get-Content -Raw -LiteralPath $stateFile | ConvertFrom-Json }
    return $null
}
function Get-OurProcess($state) {
    if (-not $state -or $state.project -ne $ProjectPath) { return $null }
    $process = Get-Process -Id ([int]$state.pid) -ErrorAction SilentlyContinue
    if (-not $process -or $process.ProcessName -notin @('powershell','pwsh')) { return $null }
    if ([Math]::Abs(($process.StartTime - [datetime]$state.started).TotalSeconds) -gt 2) { return $null }
    return $process
}
function Is-Ready([string]$Address) {
    try {
        $request = [System.Net.HttpWebRequest]::Create($Address)
        $request.Proxy = $null
        $request.Timeout = 1500
        $response = $request.GetResponse()
        try { return [int]$response.StatusCode -eq 200 }
        finally { $response.Close() }
    } catch { return $false }
}

if ($Action -eq 'Stop') {
    $state = Read-State
    $process = Get-OurProcess $state
    if (-not $process) { Write-Output 'No matching project Studio process is running.'; exit 0 }
    & taskkill.exe /PID $process.Id /T /F | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not stop the recorded project process.' }
    Remove-Item -LiteralPath $stateFile
    Write-Output 'Stopped this project Studio.'
    exit 0
}

if ($Action -eq 'Start') {
    $state = Read-State
    $process = Get-OurProcess $state
    if ($process -and [int]$state.port -eq $Port -and (Is-Ready $url)) {
        if (-not $NoOpen) { Start-Process $url }
        Write-Output "Studio already running: $url"
        exit 0
    }
    if ($process) { throw 'This project has a running or starting Studio. Check its log or stop it before another launch.' }
    $tcp = New-Object System.Net.Sockets.TcpClient
    try { $tcp.Connect('127.0.0.1',$Port); throw "Port $Port is already in use by another service. Choose another port." }
    catch [System.Net.Sockets.SocketException] { }
    finally { $tcp.Dispose() }
}

$node = if ($settings.node) { [string]$settings.node } else { 'node' }
$nodeExe = (Get-Command $node -ErrorAction Stop).Source
$cli = Join-Path $ProjectPath 'node_modules\@remotion\cli\remotion-cli.js'
if (-not (Test-Path -LiteralPath $cli)) { throw 'Install the pinned package.json dependencies, or link the verified shared node_modules first.' }
$nativeDir = if ($settings.native_dir) { [string]$settings.native_dir } else { Join-Path $ProjectPath 'node_modules\@remotion\compositor-win32-x64-msvc' }
foreach ($folder in @('tmp','npm-cache','browser-cache','logs')) {
    New-Item -ItemType Directory -Force -Path (Join-Path $runtimeWork $folder) | Out-Null
}
$env:TEMP = Join-Path $runtimeWork 'tmp'
$env:TMP = $env:TEMP
$env:NPM_CONFIG_CACHE = Join-Path $runtimeWork 'npm-cache'
$env:PUPPETEER_CACHE_DIR = Join-Path $runtimeWork 'browser-cache'
$env:Path = (Split-Path -Parent $nodeExe) + ';' + $env:Path
foreach ($tool in @('ffprobe','ffmpeg')) {
    $binary = Join-Path $nativeDir "$tool.exe"
    if (-not (Test-Path -LiteralPath $binary)) { throw "Native tool not found: $binary" }
    & $binary -version *> (Join-Path $runtimeWork "logs\$tool.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "$tool failed before opening media (exit $LASTEXITCODE). Check execution context and installation; see references/troubleshooting.md."
    }
}
if ($Action -eq 'Doctor') { Write-Output 'Node, project CLI and native media tools are available.'; exit 0 }

if ($Action -eq 'Start') {
    $escapedScript = $PSCommandPath.Replace("'","''")
    $escapedProject = $ProjectPath.Replace("'","''")
    $escapedConfig = $RuntimeConfig.Replace("'","''")
    $command = "& '$escapedScript' -Action Serve -ProjectPath '$escapedProject' -RuntimeConfig '$escapedConfig' -Port $Port -NoOpen"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
    $shellExe = (Get-Process -Id $PID).Path
    $child = Start-Process -FilePath $shellExe -ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass','-EncodedCommand',$encoded) -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeWork 'studio.stdout.log') -RedirectStandardError (Join-Path $runtimeWork 'studio.stderr.log')
    $ready = $false
    for ($attempt=0; $attempt -lt 35; $attempt++) {
        if ($child.HasExited) { throw "Studio exited. Read logs in $runtimeWork" }
        if (Is-Ready "http://127.0.0.1:$Port/") {
            $newState = Read-State
            if ($newState -and [int]$newState.pid -eq $child.Id -and $newState.project -eq $ProjectPath) { $ready = $true; break }
        }
        Start-Sleep -Milliseconds 500
    }
    if (-not $ready) { throw "Studio is not ready yet. Inspect logs in $runtimeWork before retrying." }
    if (-not $NoOpen) { Start-Process $url }
    Write-Output "Studio is running: $url"
    exit 0
}

$arguments = @($cli)
if ($Action -eq 'Serve') {
    @{pid=$PID;started=(Get-Process -Id $PID).StartTime.ToString('o');port=$Port;project=$ProjectPath} | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8
    $arguments += @('studio','src/index.ts',"--port=$Port",'--no-open')
} else {
    if (-not $OutputPath) { $OutputPath = Join-Path (Split-Path -Parent $ProjectPath) 'final.mp4' }
    $OutputPath = [IO.Path]::GetFullPath($OutputPath)
    if (Test-Path -LiteralPath $OutputPath) { throw 'Output exists; use a new filename to preserve the earlier render.' }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $OutputPath) | Out-Null
    $arguments += @('render','src/index.ts','OralVideo',$OutputPath,'--codec=h264','--concurrency=1','--offthreadvideo-video-threads=1','--offthreadvideo-cache-size-in-bytes=134217728')
    if ($settings.browser) { $arguments += "--browser-executable=$($settings.browser)" }
}
$arguments += @('--bundle-cache=false',"--binaries-directory=$nativeDir")
Push-Location -LiteralPath $ProjectPath
try { & $nodeExe @arguments; $resultCode = $LASTEXITCODE }
finally { Pop-Location }
exit $resultCode
