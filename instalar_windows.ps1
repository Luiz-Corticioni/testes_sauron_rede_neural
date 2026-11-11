# Preparação local: preserve .env e banco; atualização exige backup antes de migrar.
param(
    [string]$Python = '',
    [switch]$Atualizar,
    [switch]$Verificar
)
$ErrorActionPreference = 'Stop'
$raiz = $PSScriptRoot
Set-Location -LiteralPath $raiz
$venvPython = Join-Path $raiz '.venv\Scripts\python.exe'
function Executar([string]$Comando, [string[]]$Argumentos) {
    & $Comando @Argumentos
    if ($LASTEXITCODE -ne 0) { throw "Comando falhou (código $LASTEXITCODE): $Comando" }
}
try {
    if ($Verificar) {
        if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) { throw 'Ambiente .venv ausente. Execute primeiro instalar_windows.ps1.' }
        Executar $venvPython @('scripts/configurar_linux.py', '--verificar')
        exit 0
    }
    if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
        if (Test-Path -LiteralPath (Join-Path $raiz '.venv')) { throw '.venv existe, mas não contém Python válido. Preserve a pasta e use outra cópia do projeto.' }
        if ($Python) {
            Executar $Python @('-c', 'import sys; assert sys.version_info[:2] == (3, 12), "É necessário Python 3.12"')
            Executar $Python @('-m', 'venv', (Join-Path $raiz '.venv'))
        } else {
            Executar 'py' @('-3.12', '-m', 'venv', (Join-Path $raiz '.venv'))
        }
    }
    Executar $venvPython @('-c', 'import sys; assert sys.version_info[:2] == (3, 12), "O ambiente precisa usar Python 3.12"')
    Executar $venvPython @('-m', 'pip', 'install', '--only-binary=:all:', '-r', 'requirements.txt')
    Executar $venvPython @('-m', 'pip', 'check')
    $opcoes = @('scripts/configurar_linux.py')
    if ($Atualizar) { $opcoes += '--atualizar' }
    Executar $venvPython $opcoes
} catch {
    Write-Error "Instalação interrompida: $_"
    exit 1
}
