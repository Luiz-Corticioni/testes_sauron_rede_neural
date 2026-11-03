# Homologação da cobertura declarada

Use banco e ativos de teste. Evidências devem dizer que o cenário é sintético e não corresponde a coleta real.

1. Cadastre dois ativos operacionais A e B e uma relação REDE A→B, TCP/443, escopo `homologacao`. Use observação de hoje e revisão daqui a dez dias.
2. Como Gerente, abra Relações por camada → Qualidade → Declarar perímetro. Nome: `homologacao`; descreva o cenário e selecione A e B.
3. Consulte REDE nesse perímetro. Esperado: denominador 2, dois ativos com vínculos elegíveis (100%), nenhuma revisão completa (0%). O grafo do escopo deve conter apenas os membros operacionais declarados.
4. No item A, abra “Registrar nova revisão”. Declare relações revisadas, descreva a verificação sintética, observação de hoje e revisão daqui a vinte dias.
5. Esperado: cobertura declarada 1/2 = 50%, representação por vínculos continua 2/2 = 100%. Abra o histórico pelo link da revisão.
6. Tente declarar “nenhuma relação identificada” em B. A gravação deve ser bloqueada porque há vínculo vigente incidente. Uma revisão com lacunas pode ser registrada e não deve aumentar a cobertura completa.
7. Edite a evidência da relação A→B. A revisão anterior de A deve mostrar contexto alterado e sair do numerador. Seu resultado histórico continua “relações revisadas”.
8. Declare um terceiro ativo C como membro, sem relações. Ele deve aparecer sem revisão; não recebe automaticamente uma declaração de ausência.
9. Faça uma revisão explícita de ausência em C com evidência sintética. Ela conta como revisão completa declarada, sem criar arestas ou afirmar segurança real.
10. Confira que Auditores só consultam; Operadores podem registrar revisões, mas não administrar perímetros; um revisor sem staff continua bloqueado na administração de usuários.

Um perímetro sem membros operacionais deve apresentar percentual indefinido, nunca 100%. As contagens são do recorte declarado; não comprovam cobertura de descoberta do ambiente.
