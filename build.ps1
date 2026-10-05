param(
    [switch]$PularIcone
)

Set-Location $PSScriptRoot

function Falhar([string]$mensagem) {
    Write-Host $mensagem -ForegroundColor Red
    exit 1
}

$exe = "dist\Guaxinim.exe"

if (Test-Path -LiteralPath $exe) {
    try {
        $fluxo = [System.IO.File]::Open($exe, "Open", "ReadWrite", "None")
        $fluxo.Close()
    } catch {
        Falhar "o executavel esta em uso: feche o Guaxinim.exe e rode de novo"
    }
}

if (-not $PularIcone) {
    python tools\make_icon.py
    if ($LASTEXITCODE -ne 0) { Falhar "falha ao gerar o icone" }
}

python -m PyInstaller --noconfirm --clean Guaxinim.spec
if ($LASTEXITCODE -ne 0) { Falhar "falha no PyInstaller" }

if (-not (Test-Path -LiteralPath $exe)) { Falhar "o executavel nao foi gerado em $exe" }

"{0}  ({1:N1} MB)" -f $exe, ((Get-Item -LiteralPath $exe).Length / 1MB)
