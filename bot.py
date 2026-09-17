import os
import base64
import hashlib
import hmac
import struct
import threading
import time
from datetime import datetime
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, HTTPServer

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN não configurado")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


class HealthHandler(BaseHTTPRequestHandler):
    def _is_health_path(self):
        return self.path in ("/", "/health")

    def _send_health_headers(self, body: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()

    def do_HEAD(self):
        if self._is_health_path():
            self._send_health_headers(b"feedbacks-2fa online")
            return
        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        if self._is_health_path():
            body = b"feedbacks-2fa online"
            self._send_health_headers(body)
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, *_args):
        return


def start_health_server():
    port = int(os.getenv("PORT", "10000"))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()


def money(value: str) -> str:
    try:
        amount = Decimal(value.replace("R$", "").replace(" ", "").replace(".", "").replace(",", "."))
        return f"R$ {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (InvalidOperation, ValueError):
        raise ValueError("use um valor como 3,99 ou 10.00")


def normalize_base32(secret: str) -> bytes:
    cleaned = "".join(secret.upper().split()).replace("-", "")
    if not cleaned or any(c not in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567=" for c in cleaned):
        raise ValueError("a chave deve estar em Base32")
    cleaned += "=" * ((8 - len(cleaned) % 8) % 8)
    try:
        return base64.b32decode(cleaned, casefold=True)
    except Exception as exc:
        raise ValueError("chave Base32 inválida") from exc


def totp(secret: str, timestamp: int | None = None) -> tuple[str, int]:
    key = normalize_base32(secret)
    now = int(timestamp or time.time())
    counter = now // 30
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    code = str(binary % 1_000_000).zfill(6)
    return code, 30 - (now % 30)


class TOTPModal(discord.ui.Modal, title="Gerar código 2FA"):
    secret = discord.ui.TextInput(
        label="Chave secreta Base32",
        placeholder="Ex.: JBSWY3DPEHPK3PXP",
        required=True,
        min_length=8,
        max_length=128,
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            code, remaining = totp(str(self.secret))
        except ValueError as exc:
            await interaction.response.send_message(f"Chave inválida: {exc}", ephemeral=True)
            return

        await interaction.response.send_message(
            f"Código 2FA: **{code}**\nExpira em aproximadamente **{remaining}s**.\n\n"
            "A chave foi usada somente nesta resposta e não foi armazenada pelo bot.",
            ephemeral=True,
        )


class Generate2FAButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="GERAR 2FA",
            style=discord.ButtonStyle.success,
            custom_id="feedbacks_2fa:generate",
        )

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TOTPModal())


class Generate2FAView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Generate2FAButton())


class Configure2FAModal(discord.ui.Modal, title="Configurar painel 2FA"):
    description = discord.ui.TextInput(
        label="Descrição do painel",
        placeholder="Clique no botão abaixo para gerar seu código.",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=4000,
    )
    button_name = discord.ui.TextInput(
        label="Nome do botão",
        placeholder="GERAR 2FA",
        required=False,
        max_length=80,
    )

    def __init__(self, channel: discord.abc.Messageable):
        super().__init__()
        self.channel = channel

    async def on_submit(self, interaction: discord.Interaction):
        description = str(self.description).strip() or "Clique no botão abaixo para gerar seu código 2FA."
        button_name = str(self.button_name).strip() or "GERAR 2FA"
        if len(button_name) > 80:
            button_name = button_name[:80]

        embed = discord.Embed(
            title="🔐 Configuração 2FA",
            description=description,
            color=discord.Color.green(),
        )
        embed.set_footer(text="A resposta do código é privada. Não compartilhe sua chave secreta.")

        view = Generate2FAView()
        view.children[0].label = button_name
        await interaction.response.send_message(embed=embed, view=view)


class FeedbackModal(discord.ui.Modal, title="Criar card de feedback"):
    produto = discord.ui.TextInput(label="Texto do feedback/produto", max_length=100, required=True)
    subtotal = discord.ui.TextInput(label="Subtotal", placeholder="3,99", max_length=20, required=True)
    pago = discord.ui.TextInput(label="Valor informado", placeholder="3,99", max_length=20, required=True)
    autor = discord.ui.TextInput(label="Nome ou @ exibido", max_length=80, required=False)
    data_hora = discord.ui.TextInput(label="Data e hora exibidas", placeholder="16/09 - 20:59", max_length=40, required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            subtotal = money(str(self.subtotal))
            pago = money(str(self.pago))
        except ValueError as exc:
            await interaction.response.send_message(f"Valor inválido: {exc}", ephemeral=True)
            return

        shown_date = str(self.data_hora).strip() or datetime.now().strftime("%d/%m - %H:%M")
        shown_author = str(self.autor).strip() or interaction.user.display_name
        embed = discord.Embed(color=0x111318)
        embed.set_author(name=f"{shown_author}   •   {shown_date}")
        embed.title = "🟢 Feedback recebido"
        embed.description = (
            "**ATIVIDADE FICTÍCIA / SIMULAÇÃO**\n\n"
            "**ITEM / EXPERIÊNCIA**\n"
            f"{self.produto}\n\n"
            "**SUBTOTAL**\n"
            f"`{subtotal}`\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "**VALOR INFORMADO**\n"
            f"# {pago}\n\n"
            "_Card visual para testes e estudos; não representa uma transação._"
        )
        embed.set_footer(text="Feedback visual")
        await interaction.response.send_message(embed=embed)


@bot.event
async def on_ready():
    bot.add_view(Generate2FAView())
    try:
        synced = await bot.tree.sync()
        print(f"Online como {bot.user} — {len(synced)} comandos sincronizados")
    except Exception as exc:
        print(f"Falha ao sincronizar comandos: {exc}")


@bot.tree.command(name="feedback", description="Cria um card visual de feedback para estudos")
@app_commands.checks.has_permissions(manage_messages=True)
async def feedback(interaction: discord.Interaction):
    await interaction.response.send_modal(FeedbackModal())


@bot.tree.command(name="configurar2fa", description="Publica um painel 2FA no canal atual")
@app_commands.checks.has_permissions(manage_messages=True)
async def configurar2fa(interaction: discord.Interaction):
    await interaction.response.send_modal(Configure2FAModal(interaction.channel))


@bot.tree.command(name="health", description="Verifica se o bot está online")
async def health(interaction: discord.Interaction):
    await interaction.response.send_message("online", ephemeral=True)


@configurar2fa.error
@feedback.error
async def command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        message = "Você precisa da permissão Gerenciar mensagens para usar este comando."
    else:
        message = "Não foi possível executar o comando."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


start_health_server()
bot.run(TOKEN)
