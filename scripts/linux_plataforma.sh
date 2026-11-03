#!/usr/bin/env bash
# Função pura compartilhada pelo bootstrap e seus testes.
escolher_pacotes() {
    local distro="$1" versao="$2"
    case "$distro" in
        fedora) PACOTES=(ca-certificates python3.12) ;;
        rhel|rocky|almalinux|centos)
            case "$versao" in
                ''|[0-8]|[0-8].*|9|9.[0123])
                    echo 'Suporte automático: RHEL/compatíveis 9.4+. Use --sem-pacotes --python PATH para Python 3.12 já provisionado.' >&2
                    return 2 ;;
            esac
            PACOTES=(ca-certificates python3.12 python3.12-pip) ;;
        *) echo 'Instalação de pacotes suportada em Fedora/RHEL. Para outro Linux com Python 3.12, use --sem-pacotes.' >&2; return 2 ;;
    esac
}
