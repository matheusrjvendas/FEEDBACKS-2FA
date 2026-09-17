# Feedbacks 2FA — bot Discord

Bot Discord com dois recursos separados:

- `/feedback`: abre um formulário e publica um card visual de feedback para estudos. O card é identificado como atividade fictícia e não representa transação.
- `/configurar2fa`: disponível para membros com a permissão **Gerenciar mensagens**. Abre um modal para informar a descrição e o nome do botão e publica um painel no canal em que o comando foi executado.
- O painel tem um botão verde, com texto padrão **GERAR 2FA**. Ao clicar, o usuário recebe um modal privado para inserir uma chave TOTP Base32 e recebe o código somente em resposta efêmera.
- `/health`: resposta privada para verificar se o bot está online; o mesmo endpoint HTTP é usado pelo Render.

## TOTP e privacidade

A geração é local e usa Base32, HMAC-SHA1, 6 dígitos e janela de 30 segundos, compatível com RFC 6238 e autenticadores comuns quando a conta usa esses parâmetros. O bot não acessa nem raspa sites externos. A chave não é armazenada, logada ou publicada no canal.

## Execução local

Instale Python 3.11 ou superior, execute `pip install -r requirements.txt`, copie `.env.example` para `.env`, preencha `DISCORD_TOKEN` com o token do bot Discord e execute `python bot.py`.

O bot precisa do escopo `bot` e `applications.commands`. Para usar `/feedback` e `/configurar2fa`, o membro precisa de `Gerenciar mensagens`.

## Deploy no Render — New Web Service

Crie um **New Web Service** usando este repositório. Use `pip install -r requirements.txt` no Build Command e `python bot.py` no Start Command. O bot abre a porta fornecida pelo Render em `PORT` e responde em `/health`. No painel do Render, adicione `DISCORD_TOKEN` como variável secreta. Nunca publique esse valor no GitHub.

## Segurança

Não coloque tokens de Discord, GitHub ou chaves TOTP em commits. A chave TOTP deve ser obtida pelo titular da conta em uma fonte oficial e inserida apenas em uma resposta efêmera.
