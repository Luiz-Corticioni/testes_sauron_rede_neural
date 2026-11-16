# Preparação do servidor da faculdade

Foram validadas localmente as configurações Compose da faculdade e de HTTPS. A primeira tentativa de validar HTTPS falhou porque `SAURON_PUBLIC_HOST` não estava definido; com domínio fictício na variável do processo, ambas passaram em `docker compose config --quiet`. Nenhum serviço foi criado no servidor da faculdade.

O roteiro agora descreve um túnel SSH para o endereço informado pelo usuário, o uso explícito do nome do container na coleta de 24 horas e as verificações de porta e permissão. O nome explícito evita que a coleta consulte por engano o projeto Compose padrão. O uso de loopback mantém a aplicação inacessível diretamente de outras máquinas; a exigência de acesso da faculdade deve ser combinada com o docente.

Continuam pendentes: acesso real ao servidor, autorização e disponibilidade do Docker, definição do modo de acesso pelo professor, implantação, validação de backup e coleta real de 24 horas. Esses pontos não podem ser demonstrados por uma validação local de Compose.
