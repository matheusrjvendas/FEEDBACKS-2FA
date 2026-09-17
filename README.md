# Feedbacks 2FA — bot Discord

Bot Discord com dois recursos separados:

- `/feedback`: abre um formulário e publica um card visual de feedback para estudos. O card é identificado como atividade fictícia e não representa transação.
- `/configurar2fa`: recebe uma chave TOTP em modal efêmero e gera localmente um código de 6 dígitos, usando Base32, HMAC-SHA1 e janela de 30 segundos. A chave não é armazenada nem enviada a serviços externos.
- `/health`: resposta privada para verificar se o bot está online.

## Execução local

1. Instale Python 3.11 ou superior.
2. Execute `pip install -r requirements.txt`.
3. Copie `.env.example` para `.env` e preencha `DISCORD_TOKEN` com o token do bot Discord.
4. Execute `python bot.py`.

O bot precisa do escopo `bot` e `applications.commands`. Para usar `/feedback`, o membro precisa de `Gerenciar mensagens`.

## Deploy no Render

Crie um serviço do tipo Worker usando este repositório. O `render.yaml` já define o comando de instalação e inicialização. No painel do Render, adicione `DISCORD_TOKEN` como variável secreta. Nunca publique esse valor no GitHub.

## Segurança

Não coloque tokens de Discord, GitHub ou chaves TOTP em commits. A chave TOTP deve ser obtida pelo titular da conta em uma fonte oficial e inserida apenas em uma resposta efêmera.
