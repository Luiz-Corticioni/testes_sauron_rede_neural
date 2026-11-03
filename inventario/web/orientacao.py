"""Orientação curta por tela, sem consultas de banco ou rede."""

GLOSSARIO = [
    (
        "CVE",
        "Identificador público de uma vulnerabilidade. Confirme produto, versão e configuração antes de vinculá-la a um ativo.",
    ),
    (
        "CVSS 3.1 e 4.0",
        "Notas de gravidade de 0 a 10, com métodos diferentes. O Sauron calcula a base 3.1 pelo vetor; a nota 4.0 vem da NVD e mantém o publicador. Diferença de nota não é probabilidade de ataque.",
    ),
    (
        "Vetor CVSS",
        "Registra como a nota foi avaliada. Em 3.1: AV acesso, AC complexidade, PR privilégios, UI interação, S escopo e C/I/A impactos. Em 4.0 há requisitos de ataque (AT) e impactos separados no sistema vulnerável e em sistemas seguintes.",
    ),
    (
        "Faixas de gravidade",
        "0: nenhuma; 0,1–3,9: baixa; 4,0–6,9: média; 7,0–8,9: alta; 9,0–10: crítica. Compare a versão e a origem junto da nota.",
    ),
    (
        "NVD e publicador",
        "A NVD, do NIST, reúne registros e avaliações, inclusive de fornecedores e CNAs (organizações que atribuem CVEs). Consulta e cache têm data; falta de nota não significa zero.",
    ),
    (
        "KEV",
        "Known Exploited Vulnerabilities: catálogo da CISA de falhas com exploração conhecida no mundo real. Não estar no catálogo não comprova segurança. Confirme se seu ativo é afetado e priorize o tratamento.",
    ),
    (
        "EPSS",
        "Estimativa da FIRST da chance de exploração de uma CVE nos próximos 30 dias. Não é CVSS nem chance de comprometimento de um equipamento específico. Confira a data; valores estimados pelo simulador são hipóteses.",
    ),
    (
        "CPE",
        "Identifica produto e versão para pesquisar aplicabilidade. Confira o componente instalado; uma correspondência ou sugestão ainda exige revisão.",
    ),
    (
        "C–I–A e criticidade",
        "Confidencialidade, integridade e disponibilidade descrevem o impacto no negócio. No cadastro, valores 1–4 vão de menor a maior importância. No CVSS ambiental, 1 corresponde a baixo, 2 a médio e 3/4 a alto. Esses valores orientam prazos e ponderação do relatório.",
    ),
    (
        "Incidência e aceite",
        "Incidência liga uma falha a um ativo. Aberta, em tratamento e aceita continuam no risco. Aceite registra uma decisão e um prazo; não remove a vulnerabilidade. Correção/mitigação precisam de evidência e, nos casos sensíveis, de segundo usuário.",
    ),
    (
        "Sistema imune",
        "Recomenda possíveis vínculos por CPE/faixa ou similaridade. Afinidade não é probabilidade. Revise evidências antes de confirmar; sugestões ainda não confirmadas não entram no risco.",
    ),
    (
        "SLA e MTTR",
        "SLA é o prazo de tratamento definido pela política. MTTR é o tempo médio observado até a correção; acompanhe atrasos e mantenha o histórico de decisões.",
    ),
]

GUIAS = {
    "dashboard": (
        "Como interpretar o panorama",
        [
            "Comece pelos ativos afetados, KEV e prazos; use a ficha do ativo para conferir contexto e responsável.",
            "O índice 0–100 resume o risco matricial. Não é nota CVSS nem probabilidade. A simulação mostra um cenário e preserva o inventário.",
        ],
    ),
    "ativos": (
        "Cadastre o contexto antes de avaliar risco",
        [
            "Informe produto/versão, responsável, sala, exposição e importância de C–I–A. Dados incompletos reduzem a qualidade da análise.",
            "Abra o ativo para vincular vulnerabilidades confirmadas, componentes e fornecedores dos quais ele depende.",
        ],
    ),
    "vulnerabilidades": (
        "Gravidade e aplicabilidade",
        [
            "CVE identifica a falha; CVSS mede gravidade. A versão e o publicador fazem parte da nota.",
            "Use Comparar CVSS para recalcular 3.1 e consultar 4.0. Confirme produto/versão antes de vincular a um ativo.",
        ],
    ),
    "cves": (
        "Use a inteligência externa com contexto",
        [
            "KEV é o catálogo da CISA de falhas com exploração conhecida, não um ranking de frequência de ataques.",
            "Consulte a NVD, confira data, publicador e vetor. Revisar cadastro é uma etapa posterior; uma busca não confirma uma falha no seu ativo.",
        ],
    ),
    "comparar_cvss": (
        "O que esta comparação confere",
        [
            "A diferença entre 3.1 e 4.0 mostra mudança de avaliação entre modelos. Não use essa diferença como probabilidade ou como risco matricial.",
            "A comparação 3.1 NVD − local confere a fórmula para o mesmo vetor. O 4.0 é exibido como publicado, com validação de estrutura e sem recálculo local.",
        ],
    ),
    "imune": (
        "Revise cada recomendação",
        [
            "Uma hipótese por similaridade não comprova vulnerabilidade. Confira componente, versão e sinais antes de confirmar.",
            "A força da memória diminui para ordenar sugestões; não muda a nota CVSS. Tolerâncias e linhas de base precisam de evidência e prazo quando aplicável.",
        ],
    ),
    "alertas": (
        "Da fila à decisão",
        [
            "Reconhecer um alerta registra leitura, sem corrigir sua causa. Defina responsável, prazo e evidência de tratamento.",
            "Aceites mantêm o risco no cálculo. Decisões sensíveis exigem outro aprovador; alterações materiais devem ser aprovadas novamente.",
        ],
    ),
    "modo_euler": (
        "Métodos e unidades",
        [
            "Derivadas estimam variação; Simpson e trapézios aproximam integrais. O resultado depende do domínio da função e do passo; compare passos menores para conferir convergência.",
            "No histórico, risco-dia soma risco × duração com valor constante à esquerda entre snapshots. A tendência usa regressão; poucas amostras não permitem conclusão.",
        ],
    ),
    "matrizes": (
        "Como ler M, A e x",
        [
            "M liga ativo a falha; v contém as notas. No perfil puro, b=Mv é o risco próprio. A[i,j] transmite influência do fornecedor j para o dependente i.",
            "O sistema resolve (I−A)x=b. x pode ultrapassar 10 porque agrega falhas e dependências. Resíduo pequeno confere a conta, sem comprovar os dados de entrada.",
        ],
    ),
    "mapa": (
        "A seta mostra influência",
        [
            "A seta vai do fornecedor para quem depende dele. Peso maior representa maior influência no modelo, sem ser probabilidade de ataque.",
            "A exibição limita o número de nós; o cálculo usa o inventário completo. Ciclos são aceitos quando o modelo é estável.",
        ],
    ),
    "prioridades": (
        "Prioridade considera contexto e ganho",
        [
            "A ordem considera a maior nota ambiental nos ativos afetados e o ganho estimado de correção. Confira também KEV, prazo e impacto no negócio.",
            "O ganho representa redução modelada do risco ao corrigir a falha. Não é a diferença entre CVSS 3.1 e 4.0.",
        ],
    ),
    "montecarlo": (
        "Simule cenários de custo",
        [
            "Revise custos, exposição e EPSS antes de simular. Sem EPSS recente e coerente com a origem, o cálculo fica indisponível e mostra as pendências.",
            "A média e o P95 resumem cenários hipotéticos de 30 dias. Os custos e fatores precisam de justificativa; o resultado não é uma previsão financeira nem um modelo FAIR completo.",
        ],
    ),
    "software": (
        "Informe componentes verificáveis",
        [
            "Cadastre produto, fornecedor e versão; use CPE quando conhecido. O catálogo de software não é uma comprovação automática de vulnerabilidade."
        ],
    ),
    "importar": (
        "Confira antes de aplicar",
        [
            "Faça primeiro a validação sem gravação, leia os erros e confira os vínculos. Só depois aplique a importação."
        ],
    ),
    "auditoria": (
        "Evidência de alterações",
        [
            "A trilha registra autoria e decisões. A verificação confere a cadeia e as âncoras disponíveis; falhas precisam de investigação.",
            "Backup cifrado e cópia externa das âncoras complementam a trilha. Exportação de inventário não substitui backup restaurável.",
        ],
    ),
    "incidencias": (
        "Estado da falha no ativo",
        [
            "Aguardando confirmação fica fora do cálculo. Aberta, em tratamento e aceita entram no risco; aceite não significa correção.",
            "Revise prazos, evidências e decisões pendentes na fila de alertas.",
        ],
    ),
    "dependencias": (
        "Registre quem depende de quem",
        [
            "Fornecedor j influencia dependente i: A[i,j]. Use pesos entre 0 e 1, sem autorreferência, respeitando a estabilidade validada pelo sistema."
        ],
    ),
    "salas": (
        "Estruture o inventário",
        [
            "Organize salas e subsetores, tipos de ativo permitidos e responsáveis. Alocação excepcional exige justificativa e autorização."
        ],
    ),
}


def contexto_orientacao(request):
    nome = getattr(getattr(request, "resolver_match", None), "url_name", "")
    return {"orientacao": GUIAS.get(nome), "ajuda_tarefa": AJUDA_TAREFAS.get(nome)}


# O mesmo formato torna objetivo, exemplo, leitura e próximo passo fáceis de localizar.
AJUDA_TAREFAS = {
    "dashboard": ("Panorama para planejar o tratamento", "Identificar onde investigar primeiro e quais decisões acompanhar.",
        "Exemplo didático: uma falha KEV em servidor de pagamentos pede conferir aplicabilidade, responsável e prazo.",
        "O índice resume a política do inventário. Não equivale a probabilidade nem substitui a evidência de instalação.",
        "Abra a ficha do ativo e suas incidências antes de decidir uma correção ou aceite."),
    "incidencias": ("Acompanhar uma falha em cada ativo", "Registrar confirmação, tratamento, evidência e revisão de decisões.",
        "Exemplo didático: a mesma CVE no servidor A e no B gera duas incidências; corrigir A não corrige B.",
        "Sugerida pede investigação. Aceita continua sendo risco. Uma simulação não muda o status de nenhuma incidência.",
        "Confira produto/versão e use Editar para registrar tratamento; decisões sensíveis pedem outro aprovador."),
    "ssvc_incidencia": ("Transformar contexto em uma decisão SSVC", "Documentar a urgência e a ação com respostas sustentadas por evidências.",
        "Exemplo didático: KEV sustenta exploração ativa da CVE; a exposição e o impacto deste ativo ainda precisam de avaliação.",
        "A ação vem da tabela versionada. Reavaliar contexto não significa que a decisão anterior foi apagada.",
        "Descreva remediação, evidências e prazo de revisão; volte quando exposição ou informações relevantes mudarem."),
    "documentos": ("Importar componentes com origem rastreável", "Receber CycloneDX/OpenVEX e conferir o que a fonte declarou.",
        "Exemplo didático: importar duas vezes a mesma SBOM de uma aplicação deve preservar a identidade dos componentes, sem duplicar o risco.",
        "Prévia não grava. VEX é uma declaração; o hash detecta alteração do arquivo, sem autenticar o autor.",
        "Escolha ativo, origem e escopo, faça a prévia e confira. Para gravar, selecione novamente o arquivo e marque a opção de gravação."),
    "grafo_relacoes": ("Conferir caminhos registrados", "Comparar alcance de rede, identidade ou negócio dentro de um escopo.",
        "Exemplo didático: A→B e B→C resultam em dois saltos de A até C. Uma rota alternativa pode preservar o alcance ao retirar um vínculo.",
        "Caminho cadastrado não comprova exploração ou encaminhamento real. As camadas não são concatenadas automaticamente.",
        "Escolha camada/escopo e origem, confira as evidências dos passos e consulte a cobertura do mesmo perímetro."),
    "qualidade_relacoes": ("Identificar lacunas na revisão", "Distinguir coleta ausente, revisão incompleta e ausência declarada de vínculos.",
        "Exemplo didático: 8 de 10 membros operacionais com revisão completa e contexto preservado representam 80% de cobertura declarada.",
        "Os 80% não são um percentual de segurança. Um perímetro vazio não equivale a 100% revisado.",
        "Filtre as pendências e abra Registrar nova revisão no ativo; registre fontes e limitações da verificação."),
    "revisar_cobertura": ("Registrar uma verificação explicável", "Guardar quem verificou o recorte, quando e quais limitações encontrou.",
        "Exemplo didático: se um vínculo vigente venceu, registre lacunas ou revise o vínculo; não declare ausência para ocultar a pendência.",
        "Cada registro é histórico. O prazo máximo é 90 dias após a observação; contexto alterado exige outra revisão.",
        "Confira o resumo carregado, descreva o procedimento e escolha o resultado que sua evidência sustenta."),
    "montecarlo": ("Comparar custos hipotéticos em 30 dias", "Entender como hipóteses de custo e correção alteram os cenários do período.",
        "Exemplo didático: média de R$ 10 mil antes e R$ 7 mil após uma correção indica redução modelada de R$ 3 mil em 30 dias.",
        "Média não é valor garantido. P95 é um percentil dos cenários, sem garantir 95% de confiança sobre perdas reais.",
        "Confira EPSS, justifique os custos e compare hipóteses. Leve ao gestor as premissas e as pendências junto dos valores."),
    "modo_euler": ("Explorar cálculos com unidades claras", "Conferir funções, taxas e cenários estruturais do inventário.",
        "Exemplo didático: a integral de 10 pontos de risco durante 3 dias é 30 pontos de risco × dias, sem representar reais.",
        "Resíduo pequeno ou convergência conferem a operação matemática; a fidelidade do cadastro exige revisão separada.",
        "Escolha o cálculo pela pergunta, confira unidade e período e compare entradas antes de usar o resultado em uma decisão."),
}

GLOSSARIO.extend([
    ("PURL e SBOM", "PURL identifica um pacote e sua versão. SBOM descreve componentes declarados por uma fonte; a presença no documento não comprova instalação atual."),
    ("VEX", "Declaração de aplicabilidade de uma vulnerabilidade a um produto. O autor e o escopo precisam de conferência; não encerra incidências automaticamente."),
    ("SSVC", "Tabela de decisão que considera exploração e contexto para recomendar uma ação. Dados desconhecidos deixam a decisão pendente; não é uma nova nota de gravidade."),
    ("Cobertura declarada", "Fração dos membros operacionais do perímetro com revisão completa, no prazo e contexto preservado. Não é percentual de segurança nem mede os ativos que ainda não foram descobertos."),
    ("Média, mediana e P95", "Média: soma dividida pelo número de cenários. Mediana: metade fica de cada lado. P95: 95% dos cenários calculados ficam até o valor, sem garantir cobertura de perdas reais."),
])
