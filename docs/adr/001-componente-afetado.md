# 001 — Componente afetado

FK opcional Incidencia.software identifica o componente confirmado. A referência deve
pertencer ao mesmo ativo. O backfill escolhe apenas correspondência única de nome/CPE
na descrição/observação; quando existe só um componente ele é o candidato.
Casos ambíguos conservam NULL e aprendem somente o perfil do sistema operacional,
sem escolher o primeiro componente por ordem alfabética. A reversão remove o vínculo
inferido junto com o campo, sem alterar os componentes.
