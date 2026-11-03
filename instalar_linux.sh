#!/usr/bin/env bash
# Fedora e RHEL 9.4+/compatíveis. Execute como usuário comum.
set -Eeuo pipefail
umask 077
trap 'printf "Falha na instalação (linha %s). A inicialização foi interrompida.\n" "$LINENO" >&2' ERR
RAIZ="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SEM_PACOTES=0
SIMULAR=0
VERIFICAR=0
PYTHON=""
ARGS=()
while (($#)); do
    case "$1" in
        --sem-pacotes) SEM_PACOTES=1; shift ;;
        --simular) SIMULAR=1; shift ;;
        --verificar) VERIFICAR=1; SEM_PACOTES=1; shift ;;
        --python)
            [[ $# -ge 2 ]] || { echo 'Informe o caminho após --python.' >&2; exit 2; }
            PYTHON="$2"; shift 2 ;;
        --host)
            [[ $# -ge 2 ]] || { echo 'Informe o nome após --host.' >&2; exit 2; }
            ARGS+=("$1" "$2"); shift 2 ;;
        --https|--atualizar) ARGS+=("$1"); shift ;;
        --ajuda|-h|--help)
            cat <<'AJUDA'
Uso: bash instalar_linux.sh [opções]
  --simular       Mostra o plano sem instalar ou criar arquivos.
  --sem-pacotes   Usa Python 3.12 já instalado; dispensa dnf/sudo.
  --python PATH   Escolhe um interpretador Python 3.12.
  --verificar     Verifica instalação existente; não instala dependências.
  --host DNS --https  Configura instalação nova para proxy HTTPS.
  --atualizar     Autoriza migrações de banco existente após backup cifrado.
Padrão: instalação local, acesso em 127.0.0.1:8000, ambiente .venv-linux.
Não execute o instalador com sudo. Só a etapa dnf pede privilégio.
AJUDA
            exit 0 ;;
        *) printf 'Opção desconhecida: %s\n' "$1" >&2; exit 2 ;;
    esac
done
if [[ "$(uname -s)" != Linux ]]; then
    echo 'Execute este script dentro de um Linux. No Windows, use o instalador .bat.' >&2
    exit 2
fi
if [[ $SEM_PACOTES == 0 ]]; then
    [[ -r /etc/os-release ]] || { echo '/etc/os-release indisponível.' >&2; exit 2; }
    # Arquivo de identificação pertencente ao sistema operacional.
    . /etc/os-release
    . "$RAIZ/scripts/linux_plataforma.sh"
    escolher_pacotes "${ID:-}" "${VERSION_ID:-}"
    printf 'Pacotes via dnf:'; printf ' %s' "${PACOTES[@]}"; printf '\n'
fi
if [[ $SIMULAR == 1 ]]; then
    printf '%s\n' 'Plano: Python 3.12 → .venv-linux → requirements.txt → pip check → .env preservado/criado → backup se atualização → migrações/grupos/estáticos → âncora → diagnóstico.'
    exit 0
fi
if [[ $EUID == 0 ]]; then
    echo 'Execute como usuário comum. O instalador chama sudo somente para instalar pacotes do sistema.' >&2
    exit 2
fi
if [[ $SEM_PACOTES == 0 ]]; then
    command -v dnf >/dev/null || { echo 'dnf não encontrado.' >&2; exit 2; }
    command -v sudo >/dev/null || { echo 'sudo não encontrado. Peça ao administrador os pacotes e use --sem-pacotes.' >&2; exit 2; }
    sudo dnf install -y "${PACOTES[@]}"
fi
if [[ $VERIFICAR == 1 ]]; then
    [[ -x "$RAIZ/.venv-linux/bin/python" ]] || { echo 'Ambiente .venv-linux ausente; execute a instalação.' >&2; exit 1; }
    exec "$RAIZ/.venv-linux/bin/python" "$RAIZ/scripts/configurar_linux.py" --verificar
fi
if [[ -z "$PYTHON" ]]; then
    PYTHON="$(command -v python3.12 || true)"
fi
[[ -n "$PYTHON" && -x "$PYTHON" ]] || { echo 'Python 3.12 não encontrado. Use --python /caminho/python3.12.' >&2; exit 2; }
"$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else "É necessário Python 3.12; o Python do sistema não será substituído.")'
if [[ -e "$RAIZ/.venv-linux" && ! -x "$RAIZ/.venv-linux/bin/python" ]]; then
    echo '.venv-linux existe e não é um ambiente Linux válido. Escolha outra cópia do projeto; nenhum arquivo foi removido.' >&2
    exit 2
fi
if [[ ! -x "$RAIZ/.venv-linux/bin/python" ]]; then
    "$PYTHON" -m venv "$RAIZ/.venv-linux"
fi
VENV="$RAIZ/.venv-linux/bin/python"
"$VENV" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 12) else "Ambiente existente incompatível com Python 3.12.")'
"$VENV" -m pip install --only-binary=:all: -r "$RAIZ/requirements.txt"
"$VENV" -m pip check
exec "$VENV" "$RAIZ/scripts/configurar_linux.py" "${ARGS[@]}"
