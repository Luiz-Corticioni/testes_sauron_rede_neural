# Não exige ativar Activate.ps1: chama diretamente o Python do ambiente.
$ErrorActionPreference = "Stop"
$sauronRaiz = Split-Path -Parent $PSScriptRoot
$sauronPython = Join-Path $sauronRaiz ".venv\Scripts\python.exe"
$sauronScript = Join-Path $PSScriptRoot "prova_24h.py"
if (Test-Path $sauronPython) {
    & $sauronPython $sauronScript @args
} else {
    py $sauronScript @args
}
exit $LASTEXITCODE
