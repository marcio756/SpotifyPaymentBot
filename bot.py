import discord
from discord.ext import commands, tasks
import datetime
from utils import load_payments, save_payments, ensure_user_month, month_translation, reset_payments, is_month_paid
from admin import AdminPaymentsView, definir_canal_lembrete, definir_canal_comandos, definir_canal_confirmacao, testar_lembrete, todos_pagamentos
from user import PaymentView, UserPaymentsView, pagar, pagamentos, ajuda
from views import ConfirmPaymentView

# Bot configuration
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.lembrete_channel_id = None
bot.commands_channel_id = None
bot.confirmation_channel_id = None


@bot.event
async def on_ready():
    """Called when the bot is ready."""
    print(f"Bot online as {bot.user}")
    payments = load_payments()
    bot.lembrete_channel_id = payments.get('settings',
                                           {}).get('lembrete_channel_id')
    bot.commands_channel_id = payments.get('settings',
                                           {}).get('commands_channel_id')
    bot.confirmation_channel_id = payments.get(
        'settings', {}).get('confirmation_channel_id')
    check_payments.start()
    check_late_payments.start()
    monthly_summary.start()


@bot.event
async def on_message(message):
    """Tracks messages to register users."""
    if message.author.bot:
        return
    try:
        current_year = str(datetime.datetime.now().year)
        current_month_en = datetime.datetime.now().strftime("%B").lower()
        current_month = month_translation.get(current_month_en,
                                              current_month_en)
        payments = load_payments()
        ensure_user_month(payments, message.author.id, current_year,
                          current_month)
        save_payments(payments, bot.lembrete_channel_id,
                      bot.commands_channel_id, bot.confirmation_channel_id)
    except Exception as e:
        print(f"Error processing message: {e}")
    await bot.process_commands(message)


@tasks.loop(time=datetime.time(
    hour=0, minute=0, tzinfo=datetime.timezone(datetime.timedelta(hours=1))))
async def check_payments():
    """Sends reminders on the 13th of each month."""
    now = datetime.datetime.now()
    if now.day != 13:
        return
    current_year = str(now.year)
    current_month_en = now.strftime("%B").lower()
    current_month = month_translation.get(current_month_en, current_month_en)

    payments = load_payments()
    if now.month == 1:
        reset_payments(payments)
        save_payments(payments, bot.lembrete_channel_id,
                      bot.commands_channel_id, bot.confirmation_channel_id)

    for user_id in payments:
        if user_id not in ('settings', 'pending_payments'):
            ensure_user_month(payments, user_id, current_year, current_month)
            if not is_month_paid(payments, user_id, current_year,
                                 current_month_en):
                user = await bot.fetch_user(int(user_id))
                if user:
                    view = PaymentView(int(user_id), current_year,
                                       current_month)
                    message = f"{user.mention}, tomorrow is the Spotify payment day for {current_month.capitalize()}/{current_year}. Have you sent the money?"
                    if bot.lembrete_channel_id:
                        reminders_channel = bot.get_channel(
                            bot.lembrete_channel_id)
                        if reminders_channel:
                            await reminders_channel.send(message, view=view)
                    else:
                        await user.send(message, view=view)


@tasks.loop(time=datetime.time(
    hour=0, minute=0, tzinfo=datetime.timezone(datetime.timedelta(hours=1))))
async def check_late_payments():
    """Notifies late payments on the 15th."""
    now = datetime.datetime.now()
    if now.day != 15:
        return
    current_year = str(now.year)
    current_month_en = now.strftime("%B").lower()
    current_month = month_translation.get(current_month_en, current_month_en)
    payments = load_payments()
    for user_id in payments:
        if user_id not in ('settings', 'pending_payments'):
            if not is_month_paid(payments, user_id, current_year,
                                 current_month_en):
                user = await bot.fetch_user(int(user_id))
                if user:
                    message = f"{user.mention}, the Spotify payment for {current_month.capitalize()}/{current_year} is overdue! Please send the money ASAP."
                    if bot.lembrete_channel_id:
                        channel = bot.get_channel(bot.lembrete_channel_id)
                        if channel:
                            await channel.send(message)
                    else:
                        await user.send(message)


@tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=datetime.timezone.utc))
async def monthly_summary():
    """Sends a monthly summary on the 1st."""
    now = datetime.datetime.now()
    if now.day != 1:
        return
    current_year = str(now.year)
    last_month_date = now.replace(day=1) - datetime.timedelta(days=1)
    last_month_en = last_month_date.strftime("%B").lower()
    last_month = month_translation.get(last_month_en, last_month_en)
    payments = load_payments()
    response = f"**Payment Summary for {last_month.capitalize()}/{current_year}**\n"
    for user_id in payments:
        if user_id not in ('settings', 'pending_payments'):
            user = await bot.fetch_user(int(user_id))
            status = "✅" if is_month_paid(payments, user_id, current_year,
                                          last_month_en) else "❌"
            response += f"{user.name}: {status}\n"
    if bot.lembrete_channel_id:
        channel = bot.get_channel(bot.lembrete_channel_id)
        if channel:
            await channel.send(response)


# Register commands
bot.add_command(definir_canal_lembrete)
bot.add_command(definir_canal_comandos)
bot.add_command(definir_canal_confirmacao)
bot.add_command(testar_lembrete)
bot.add_command(todos_pagamentos)
bot.add_command(pagar)
bot.add_command(pagamentos)
bot.add_command(ajuda)
