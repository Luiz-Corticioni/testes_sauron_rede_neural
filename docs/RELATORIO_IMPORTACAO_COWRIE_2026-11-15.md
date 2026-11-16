# Importação offline de eventos Cowrie

O Sauron aceita JSONL Cowrie, limitado a 1 MB e 500 linhas, e apresenta uma prévia antes da confirmação. São aproveitados somente conexão, login aceito e login falho, com data, IP e tipo. Outros eventos são contados como ignorados. Senhas, usuários e comandos não são gravados pelo importador; o arquivo original continua sob responsabilidade do operador. O envio e a prévia exigem proteção de transporte e controle de acesso ao ambiente.

O operador atribui um UUID ao lote e deve reutilizá-lo com o mesmo arquivo. O identificador de cada evento combina o UUID e a posição da linha; a repetição é idempotente dentro do mesmo sensor, mas usar outro UUID ou reordenar linhas pode criar duplicatas. Uma prévia assinada por dez minutos vincula usuário, sensor e conteúdo minimizado; o arquivo precisa ser reenviado. A importação reutiliza validação, auditoria e retenção existentes. Eventos não comprovam ataque e seguem sujeitos à triagem humana.

Foram executados 17 testes de Cowrie e honeypot, incluindo prévia sem gravação, confirmação, lote repetido, troca do arquivo e ausência dos segredos nos registros verificados. Não há implantação nem ingestão automática de um honeypot real; as rotinas de retenção devem estar agendadas no ambiente real e backups têm ciclo próprio.
