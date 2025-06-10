import discord
from discord.ext import commands
from discord.ui import Button, View
import datetime
from utils import load_payments, save_payments, ensure_user_month, set_payment_status, is_month_paid, get_user_payments, month_translation, check_command_channel
from user import PaymentView
from views import ConfirmPaymentView


class AdminPaymentsView(View):

    def __init__(self, user_ids, current_index, year, invoking_user_id):
        super().__init__(timeout=60)
        self.user_ids = user_ids
        self.current_index = current_index
        self.year = year
        self.invoking_user_id = invoking_user_id

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def prev_button(self, interaction: discord.Interaction,
                          button: discord.Button):
        if interaction.user.id != self.invoking_user_id:
            await interaction.response.send_message(
                "Only the user who executed the command can use this button!")
            return
        self.current_index = (self.current_index - 1) % len(self.user_ids)
        await self.update_message(interaction)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction,
                          button: discord.Button):
        if interaction.user.id != self.invoking_user_id:
            await interaction.response.send_message(
                "Only the user who executed the command can use this button!")
            return
        self.current_index = (self.current_index + 1) % len(self.user_ids)
        await self.update_message(interaction)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red)
    async def close_button(self, interaction: discord.Interaction,
                           button: discord.Button):
        if interaction.user.id != self.invoking_user_id:
            await interaction.response.send_message(
                "Only the user who executed the command can use this button!")
            return
        await interaction.message.delete()

    async def update_message(self, interaction: discord.Interaction):
        if interaction.user.id != self.invoking_user_id:
            await interaction.response.send_message(
                "Only the user who executed the command can use this button!")
            return
        user_id = self.user_ids[self.current_index]
        user = await interaction.client.fetch_user(int(user_id))
        payments = get_user_payments(load_payments(), user_id, self.year)
        response = f"**Payments for {user.name} ({self.year})**\n"
        for mes in month_translation.values():
            status = "✅" if payments.get(mes, False) else "❌"
            response += f"{mes.capitalize()}: {status}\n"
        await interaction.response.edit_message(content=response, view=self)


@commands.command()
@commands.has_permissions(administrator=True)
async def definir_canal_lembrete(ctx, channel: discord.TextChannel):
    """Sets the reminders channel."""
    if not await check_command_channel(ctx):
        return
    ctx.bot.lembrete_channel_id = channel.id
    payments = load_payments()
    save_payments(payments, ctx.bot.lembrete_channel_id,
                  ctx.bot.commands_channel_id, ctx.bot.confirmation_channel_id)
    await ctx.send(f"Reminders channel set to {channel.mention}.")


@commands.command()
@commands.has_permissions(administrator=True)
async def definir_canal_comandos(ctx, channel: discord.TextChannel):
    """Sets the commands channel."""
    if not await check_command_channel(ctx):
        return
    ctx.bot.commands_channel_id = channel.id
    payments = load_payments()
    save_payments(payments, ctx.bot.lembrete_channel_id,
                  ctx.bot.commands_channel_id, ctx.bot.confirmation_channel_id)
    await ctx.send(f"Commands channel set to {channel.mention}.")


@commands.command()
@commands.has_permissions(administrator=True)
async def definir_canal_confirmacao(ctx, channel: discord.TextChannel):
    """Sets the payment confirmation channel."""
    if not await check_command_channel(ctx):
        return
    ctx.bot.confirmation_channel_id = channel.id
    payments = load_payments()
    save_payments(payments, ctx.bot.lembrete_channel_id,
                  ctx.bot.commands_channel_id, ctx.bot.confirmation_channel_id)
    await ctx.send(f"Payment confirmation channel set to {channel.mention}.")


@commands.command()
@commands.has_permissions(administrator=True)
async def testar_lembrete(ctx):
    """Tests sending reminders."""
    if not await check_command_channel(ctx):
        return
    await ctx.send("Processing test reminder...")

    current_year = str(datetime.datetime.now().year)
    current_month_en = datetime.datetime.now().strftime("%B").lower()
    current_month_pt = month_translation.get(current_month_en,
                                             current_month_en)
    payments = load_payments()

    if not payments:
        await ctx.send("No registered users to test the reminder.")
        return

    sent = 0
    if ctx.bot.lembrete_channel_id:
        reminders_channel = ctx.bot.get_channel(ctx.bot.lembrete_channel_id)
    else:
        await ctx.send(
            "Reminders channel not set. Please use !definir_canal_lembrete.")
        return

    for user_id in payments:
        if user_id not in ('settings', 'pending_payments'):
            ensure_user_month(payments, user_id, current_year,
                              current_month_pt)
            if not is_month_paid(payments, user_id, current_year,
                                 current_month_en):
                user = await ctx.bot.fetch_user(int(user_id))
                if user:
                    view = PaymentView(int(user_id), current_year,
                                       current_month_pt)
                    message = f"[TEST] {user.mention}, tomorrow is the Spotify payment day for {current_month_pt.capitalize()}/{current_year}. Have you sent the money?"
                    await reminders_channel.send(message, view=view)
                    sent += 1

    await ctx.send(
        f"Test reminder sent to {sent} user(s) with {current_month_pt.capitalize()} unpaid."
    )


@commands.command()
@commands.has_permissions(administrator=True)
async def todos_pagamentos(ctx):
    """Shows all users' payments."""
    if not await check_command_channel(ctx):
        return
    await ctx.send("Loading all users' payments...")

    payments = load_payments()
    user_ids = [
        uid for uid in payments.keys()
        if uid not in ('settings', 'pending_payments')
    ]
    if not user_ids:
        await ctx.send("No registered users.")
        return

    current_year = str(datetime.datetime.now().year)

    async def show_page(index):
        user_id = user_ids[index]
        user = await ctx.bot.fetch_user(int(user_id))
        payments_data = get_user_payments(payments, user_id, current_year)
        response = f"**Payments for {user.name} ({current_year})**\n"
        for mes in month_translation.values():
            status = "✅" if payments_data.get(mes, False) else "❌"
            response += f"{mes.capitalize()}: {status}\n"
        view = AdminPaymentsView(user_ids, index, current_year, ctx.author.id)
        if len(user_ids) == 1:
            view.prev_button.disabled = True
            view.next_button.disabled = True
        await ctx.send(response, view=view)

    await show_page(0)
