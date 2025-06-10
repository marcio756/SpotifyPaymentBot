import json
import os
import datetime
from discord.ext import commands

# Tradução de meses
month_translation = {
    'january': 'janeiro',
    'february': 'fevereiro',
    'march': 'março',
    'april': 'abril',
    'may': 'maio',
    'june': 'junho',
    'july': 'julho',
    'august': 'agosto',
    'september': 'setembro',
    'october': 'outubro',
    'november': 'novembro',
    'december': 'dezembro'
}


def load_payments():
    """Carrega os dados do payments.json."""
    if not os.path.exists('payments.json'):
        return {'settings': {}, 'pending_payments': {}}
    try:
        with open('payments.json', 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return {'settings': {}, 'pending_payments': {}}
            return json.loads(content)
    except json.JSONDecodeError:
        print("JSON corrompido, recriando arquivo.")
        save_payments({
            'settings': {},
            'pending_payments': {}
        }, None, None, None)
        return {'settings': {}, 'pending_payments': {}}


def save_payments(payments, lembrete_channel_id, commands_channel_id,
                  confirmation_channel_id):
    """Salva os dados no payments.json."""
    try:
        with open('payments.json', 'w', encoding='utf-8') as f:
            if 'settings' not in payments:
                payments['settings'] = {}
            if 'pending_payments' not in payments:
                payments['pending_payments'] = {}
            payments['settings']['lembrete_channel_id'] = lembrete_channel_id
            payments['settings']['commands_channel_id'] = commands_channel_id
            payments['settings'][
                'confirmation_channel_id'] = confirmation_channel_id
            json.dump(payments, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erro ao salvar payments.json: {e}")


def ensure_user_month(payments, user_id, year, month):
    """Garante que um usuário tenha uma entrada para o ano/mês."""
    user_id = str(user_id)
    year = str(year)
    if user_id not in payments or user_id in ('settings', 'pending_payments'):
        payments[user_id] = {}
    if year not in payments[user_id]:
        payments[user_id][year] = {
            m: False
            for m in month_translation.values()
        }
    if month not in payments[user_id][year]:
        payments[user_id][year][month] = False


def set_payment_status(payments, user_id, year, month, status):
    """Define o status de pagamento de um mês."""
    user_id = str(user_id)
    year = str(year)
    ensure_user_month(payments, user_id, year, month)
    payments[user_id][year][month] = status


def is_month_paid(payments, user_id, year, month_en):
    """Verifica se um mês está pago."""
    user_id = str(user_id)
    year = str(year)
    month_pt = month_translation.get(month_en.lower(), month_en.lower())
    ensure_user_month(payments, user_id, year, month_pt)
    return payments[user_id][year][month_pt]


def get_user_payments(payments, user_id, year):
    """Retorna os pagamentos de um usuário para um ano."""
    user_id = str(user_id)
    year = str(year)
    ensure_user_month(payments, user_id, year, 'janeiro')
    return payments[user_id][year]


def reset_payments(payments):
    """Reseta os pagamentos para o ano atual."""
    current_year = str(datetime.datetime.now().year)
    for user_id in list(payments.keys()):
        if user_id not in ('settings', 'pending_payments'):
            payments[user_id] = {
                current_year: {
                    month: False
                    for month in month_translation.values()
                }
            }


async def check_command_channel(ctx):
    """Verifica se o comando foi usado no canal correto."""
    if ctx.bot.commands_channel_id and ctx.channel.id != ctx.bot.commands_channel_id:
        if ctx.command.name in (
                'definir_canal_comandos', 'definir_canal_lembrete',
                'definir_canal_confirmacao'
        ) and ctx.author.guild_permissions.administrator:
            return True
        await ctx.author.send(
            f"Por favor, use os comandos no canal <#{ctx.bot.commands_channel_id}>."
        )
        return False
    return True
