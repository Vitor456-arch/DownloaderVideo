param(
    [string]$FFmpegDirectory = "",
    [string]$FFmpegNoticesDirectory = "",
    [switch]$Installer
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Python 3.12 não encontrado." }
}
$python = Join-Path $PWD ".venv\Scripts\python.exe"
& $python -m pip install -r requirements-tested.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependências." }
& $python -m pip install --no-deps -e .
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar projeto." }
if ($FFmpegDirectory) {
    foreach ($binary in @("ffmpeg.exe", "ffprobe.exe")) {
        if (-not (Test-Path (Join-Path $FFmpegDirectory $binary))) { throw "$binary não encontrado." }
    }
    if (-not $FFmpegNoticesDirectory -or -not (Test-Path $FFmpegNoticesDirectory)) {
        throw "Forneça os avisos, licenças e instruções de obtenção do código-fonte correspondente do FFmpeg."
    }
    $env:DOWNLOADERVIDEO_FFMPEG_DIR = (Resolve-Path $FFmpegDirectory).Path
    $env:DOWNLOADERVIDEO_FFMPEG_NOTICES = (Resolve-Path $FFmpegNoticesDirectory).Path
} else {
    Remove-Item Env:DOWNLOADERVIDEO_FFMPEG_DIR -ErrorAction SilentlyContinue
    Remove-Item Env:DOWNLOADERVIDEO_FFMPEG_NOTICES -ErrorAction SilentlyContinue
    Write-Warning "Pacote sem FFmpeg. O usuário precisará instalá-lo pelas instruções da interface."
}
& $python -m PyInstaller --clean --noconfirm packaging\DownloaderVideo.spec
if ($LASTEXITCODE -ne 0) { throw "Falha no empacotamento." }
if ($FFmpegDirectory) {
    & $python packaging\smoke_frozen.py dist\DownloaderVideo\DownloaderVideo.exe --bundled
} else {
    & $python packaging\smoke_frozen.py dist\DownloaderVideo\DownloaderVideo.exe
}
if ($LASTEXITCODE -ne 0) { throw "Falha no teste do executável." }
if ($Installer) {
    $compiler = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if (-not $compiler) {
        $compiler = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
        if (-not (Test-Path $compiler)) { throw "Instale Inno Setup 6 para gerar o instalador." }
    } else { $compiler = $compiler.Source }
    & $compiler packaging\installer.iss
    if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar instalador." }
}
Get-ChildItem dist -File | Get-FileHash -Algorithm SHA256 | Format-Table
