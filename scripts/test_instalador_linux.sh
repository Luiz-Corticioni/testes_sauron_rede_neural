#!/usr/bin/env bash
# Testa orquestração com Python/sistema simulados, sem sudo, rede ou banco real.
set -Eeuo pipefail
RAIZ="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
. "$RAIZ/scripts/linux_plataforma.sh"
escolher_pacotes fedora 43
[[ "${PACOTES[*]}" == 'ca-certificates python3.12' ]]
escolher_pacotes rhel 9.4
[[ "${PACOTES[*]}" == 'ca-certificates python3.12 python3.12-pip' ]]
escolher_pacotes rocky 10
[[ "${PACOTES[*]}" == 'ca-certificates python3.12 python3.12-pip' ]]
if escolher_pacotes rhel 9.3 >/dev/null 2>&1; then exit 1; fi
if escolher_pacotes ubuntu 24.04 >/dev/null 2>&1; then exit 1; fi
TEMP_RAIZ="$(cd -- "${TMPDIR:-/tmp}" && pwd)"
PASTA="$(mktemp -d "$TEMP_RAIZ/sauron-installer-test.XXXXXX")"
limpar() {
    case "$PASTA" in
        "$TEMP_RAIZ"/sauron-installer-test.*) rm -rf -- "$PASTA" ;;
        *) echo 'Limpeza recusada: caminho fora da pasta temporária do teste.' >&2 ;;
    esac
}
trap limpar EXIT
# mktemp criou esta pasta exclusivamente para o teste; nenhum caminho do usuário é removido.
COPIA="$PASTA/projeto com espaços"
mkdir -p "$COPIA/scripts"
cp "$RAIZ/instalar_linux.sh" "$COPIA/"
cp "$RAIZ/scripts/linux_plataforma.sh" "$COPIA/scripts/"
printf 'Django==5.2.17\n' > "$COPIA/requirements.txt"
printf 'configuração preservada\n' > "$COPIA/.env"
export SAURON_TEST_LOG="$PASTA/comandos.log"
cat > "$PASTA/python falso" <<'PYTHON'
#!/usr/bin/env bash
set -eu
printf '%s\n' "$*" >> "$SAURON_TEST_LOG"
if [[ "${1:-}" == -m && "${2:-}" == venv ]]; then
    mkdir -p "$3/bin"
    cp -- "$0" "$3/bin/python"
    chmod +x "$3/bin/python"
fi
if [[ "${1:-}" == -m && "${2:-}" == pip && "${3:-}" == install && "${SAURON_TEST_FALHAR:-0}" == 1 ]]; then
    exit 42
fi
PYTHON
chmod +x "$PASTA/python falso"
uname() { printf 'Linux\n'; }
export -f uname
# Em CI o teste deve executar como usuário comum, tal como o instalador real.
bash "$COPIA/instalar_linux.sh" --sem-pacotes --python "$PASTA/python falso"
grep -F -- '-m pip install --only-binary=:all: -r' "$SAURON_TEST_LOG" >/dev/null
grep -F -- '-m pip check' "$SAURON_TEST_LOG" >/dev/null
grep -F -- '/scripts/configurar_linux.py' "$SAURON_TEST_LOG" >/dev/null
[[ "$(cat "$COPIA/.env")" == 'configuração preservada' ]]
: > "$SAURON_TEST_LOG"
export SAURON_TEST_FALHAR=1
if bash "$COPIA/instalar_linux.sh" --sem-pacotes --python "$PASTA/python falso"; then exit 1; fi
if grep -F -- '/scripts/configurar_linux.py' "$SAURON_TEST_LOG" >/dev/null; then exit 1; fi
: > "$SAURON_TEST_LOG"
bash "$COPIA/instalar_linux.sh" --sem-pacotes --simular
[[ ! -s "$SAURON_TEST_LOG" ]]
printf 'OK: plataforma, caminhos com espaços, sequência, preservação, interrupção e simulação.\n'
