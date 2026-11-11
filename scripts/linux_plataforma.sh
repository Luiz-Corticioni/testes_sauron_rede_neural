#!/usr/bin/env bash
# Função pura compartilhada pelo bootstrap e seus testes.
escolher_pacotes() {
    local distro="$1" versao="$2"
    case "$distro" in
        fedora) GERENCIADOR=dnf; PACOTES=(ca-certificates python3.12) ;;
        rhel|rocky|almalinux|centos)
            case "$versao" in
                ''|[0-8]|[0-8].*|9|9.[0123])
                    echo 'Suporte automático: RHEL/compatíveis 9.4+. Use --sem-pacotes --python PATH para Python 3.12 já provisionado.' >&2
                    return 2 ;;
            esac
            GERENCIADOR=dnf; PACOTES=(ca-certificates python3.12 python3.12-pip) ;;
        ubuntu)
            [[ "$versao" == 24.04 ]] || { echo 'Instale Python 3.12 e venv pelo fornecedor e use --sem-pacotes.' >&2; return 2; }
            GERENCIADOR=apt-get; PACOTES=(ca-certificates python3.12 python3.12-venv) ;;
        *) echo 'Distribuição sem instalação automática de pacotes. Instale Python 3.12 com venv e use --sem-pacotes --python CAMINHO.' >&2; return 2 ;;
    esac
}
