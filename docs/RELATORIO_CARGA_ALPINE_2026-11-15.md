# Ensaio de capacidade da imagem Alpine

Foram executados dois ensaios locais HTTP em loopback, com projetos e bancos descartáveis separados, 100 contas fictícias, quatro administradores e 96 usuários comuns. A aplicação usou o Compose com limite de 1 CPU e 512 MiB, um worker com duas threads e verificação Argon2 real. Cada fluxo realizou senha, TOTP, acesso à aplicação e verificação de autorização administrativa.

| Concorrência de clientes | Resultado | Duração total | p50 do fluxo | p95 do fluxo | Pico de memória do container |
|---|---|---:|---:|---:|---:|
| 100 | 4 administradores e 96 usuários comuns com resultados esperados | 77,84 s | 77,56 s | 77,80 s | 300,2 MiB |
| 10 | 4 administradores e 96 usuários comuns com resultados esperados | 79,69 s | 7,88 s | 8,67 s | 301,6 MiB |

As métricas de fluxo incluem o tempo de espera na barreira de sincronização e chamadas sequenciais; não representam apenas a latência de uma requisição nem devem ser comparadas como se medissem a mesma fila. O cenário de 100 clientes não apresentou falhas, mas o atraso observado é alto para uma experiência interativa e não comprova que o servidor suportará 100 usuários em produção. O pico inclui toda a vida do container, não apenas a fase de login. Nenhum dos dois ensaios registrou OOM ou reinício, e a rota de saúde respondeu HTTP 200 após a carga.

No teste adicional de tentativas incorretas, uma conta sintética recebeu cinco respostas de falha e depois HTTP 429 com `Retry-After: 900`. Os arquivos de credenciais sintéticas foram apagados e os containers de teste foram parados; seus volumes isolados permanecem. O cliente agora aceita concorrência 10, 20 ou 100; 20 não foi medido nesta etapa. Não houve teste de TLS, e-mail, rede real, múltiplos IPs, operação prolongada ou concorrência de outras funções. A recuperação observada foi a resposta de saúde após a carga, não um teste de falha de servidor ou OOM.
