import discord
from discord.ext import commands
from discord.ui import Button, View
import datetime
from utils import load_payments, save_payments, ensure_user_month, month_translation, check_command_channel, get_user_payments, set_payment_status, is_month_paid
from views import ConfirmPaymentView


class PaymentView(View):

    def __init__(self, user_id, year, month):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.year = year
        self.month = month

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def yes_button(self, interaction: discord.Interaction,
                         button: discord.Button):
        """Confirms that the user marked the payment."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Only the mentioned user can use this button!")
            return
        payments = load_payments()
        user_id_str = str(self.user_id)
        if 'pending_payments' not in payments:
            payments['pending_payments'] = {}
        if user_id_str not in payments['pending_payments']:
            payments['pending_payments'][user_id_str] = {}
        if self.year not in payments['pending_payments'][user_id_str]:
            payments['pending_payments'][user_id_str][self.year] = {}
        if self.month not in payments['pending_payments'][user_id_str][
                self.year]:
            payments['pending_payments'][user_id_str][self.year][
                self.month] = {}
            confirmation_channel = interaction.client.get_channel(
                interaction.client.confirmation_channel_id)
            if confirmation_channel:
                message = await confirmation_channel.send(
                    f"{interaction.user.mention} marked {self.month.capitalize()}/{self.year} as paid. Administrator, please confirm:",
                    view=ConfirmPaymentView(self.user_id, self.year,
                                            [self.month]))
                payments['pending_payments'][user_id_str][self.year][
                    self.month]['confirmation_message_id'] = message.id
                save_payments(payments, interaction.client.lembrete_channel_id,
                              interaction.client.commands_channel_id,
                              interaction.client.confirmation_channel_id)
                await interaction.response.edit_message(
                    content=
                    f"Payment intention for {self.month.capitalize()} registered! Awaiting admin confirmation.",
                    view=None)
            else:
                await interaction.response.send_message(
                    "Confirmation channel not found. Please contact an administrator."
                )

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def no_button(self, interaction: discord.Interaction,
                        button: discord.Button):
        """Ignores the payment action."""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "Only the mentioned user can use this button!")
            return
        await interaction.response.edit_message(
            content="Payment action ignored.", view=None)


class UserPaymentsView(View):

    def __init__(self, user_id, year, available_years, invoking_user_id):
        super().__init__(timeout=60)
        self.user_id = user_id
        self.current_year = year
        self.available_years = sorted(available_years, key=int)
        self.invoking_user_id = invoking_user_id
        self.prev_button.disabled = str(year) == min(self.available_years,
                                                     key=int)
        self.next_button.disabled = str(year) == max(self.available_years,
                                                     key=int)

    @discord.ui.button(label="Previous Year", style=discord.ButtonStyle.gray)
    async def prev_button(self, interaction: discord.Interaction,
                          button: discord.Button):
        if interaction.user.id != self.invoking_user_id:
            await interaction.response.send_message(
                "Only the user who executed the command can use this button!")
            return
        current_index = self.available_years.index(str(self.current_year))
        self.current_year = int(self.available_years[current_index - 1])
        await self.update_message(interaction)

    @discord.ui.button(label="Next Year", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction,
                          button: discord.Button):
        if interaction.user.id != self.invoking_user_id:
            await interaction.response.send_message(
                "Only the user who executed the command can use this button!")
            return
        current_index = self.available_years.index(str(self.current_year))
        self.current_year = int(self.available_years[current_index + 1])
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
        payments = get_user_payments(load_payments(), self.user_id,
                                     self.current_year)
        response = f"**Payments for {interaction.user.name} ({self.current_year})**\n"
        for mes in month_translation.values():
            status = "✅" if payments.get(mes, False) else "❌"
            response += f"{mes.capitalize()}: {status}\n"
        self.prev_button.disabled = str(self.current_year) == min(
            self.available_years, key=int)
        self.next_button.disabled = str(self.current_year) == max(
            self.available_years, key=int)
        await interaction.response.edit_message(content=response, view=self)


@commands.command()
async def pagar(ctx, *, months):
    """Marks months as paid for admin confirmation."""
    if not await check_command_channel(ctx):
        return
    current_year = str(datetime.datetime.now().year)
    months_list = [month.lower() for month in months.split()]
    valid_months = [
        month for month in months_list if month in month_translation.values()
    ]

    if not valid_months:
        await ctx.send("Please specify valid months (e.g., janeiro fevereiro)."
                       )
        return

    payments = load_payments()
    user_id = str(ctx.author.id)
    if 'pending_payments' not in payments:
        payments['pending_payments'] = {}
    if user_id not in payments['pending_payments']:
        payments['pending_payments'][user_id] = {}
    if current_year not in payments['pending_payments'][user_id]:
        payments['pending_payments'][user_id][current_year] = {}

    pending_months = []
    already_paid = []
    confirmation_channel = ctx.bot.get_channel(ctx.bot.confirmation_channel_id)
    commands_channel = ctx.bot.get_channel(ctx.bot.commands_channel_id)
    for month in valid_months:
        if not is_month_paid(payments, user_id, current_year, month):
            if month not in payments['pending_payments'][user_id][
                    current_year]:
                payments['pending_payments'][user_id][current_year][month] = {}
                pending_months.append(month)
        else:
            already_paid.append(month)

    if pending_months and confirmation_channel and commands_channel:
        view = ConfirmPaymentView(ctx.author.id, current_year, pending_months)
        confirmation_message = await confirmation_channel.send(
            f"{ctx.author.mention} marked {', '.join(pending_months).capitalize()}/{current_year} as paid. Administrator, please confirm:",
            view=view)
        response_message = await ctx.send(
            f"Payment intention for {', '.join(pending_months).capitalize()} registered! Awaiting admin confirmation."
        )
        for month in pending_months:
            payments['pending_payments'][user_id][current_year][month][
                'confirmation_message_id'] = confirmation_message.id
            payments['pending_payments'][user_id][current_year][month][
                'response_message_id'] = response_message.id
        save_payments(payments, ctx.bot.lembrete_channel_id,
                      ctx.bot.commands_channel_id,
                      ctx.bot.confirmation_channel_id)
    elif pending_months:
        await ctx.send(
            "Confirmation channel or commands channel not found. Please contact an administrator."
        )

    if already_paid:
        await ctx.send(
            f"The months {', '.join(already_paid).capitalize()} are already paid and were not added."
        )


@commands.command()
async def pagamentos(ctx):
    """Shows the user's payments."""
    if not await check_command_channel(ctx):
        return
    user_id = ctx.author.id
    current_year = datetime.datetime.now().year
    payments = load_payments()
    user_id_str = str(user_id)

    if user_id_str not in payments or user_id_str in ('settings',
                                                      'pending_payments'):
        await ctx.send("You have no registered payments.")
    else:
        available_years = [
            year for year in payments[user_id_str].keys() if year.isdigit()
        ]
        if not available_years:
            await ctx.send("You have no registered years.")
        else:
            payments_year = get_user_payments(payments, user_id, current_year)
            response = f"**Payments for {ctx.author.name} ({current_year})**\n"
            for mes in month_translation.values():
                status = "✅" if payments_year.get(mes, False) else "❌"
                response += f"{mes.capitalize()}: {status}\n"
            view = UserPaymentsView(user_id, current_year, available_years,
                                    ctx.author.id)
            await ctx.send(response, view=view)


@commands.command()
async def ajuda(ctx):
    """Shows the list of commands."""
    if not await check_command_channel(ctx):
        return
    response = "**Bot Commands**\n"
    response += "```"
    response += "!pagar <months>\n"
    response += "   Marks one or more months as paid, awaiting admin confirmation (e.g., !pagar janeiro fevereiro).\n\n"
    response += "!pagamentos\n"
    response += "   Shows your payment status for the current year.\n\n"
    response += "!todos_pagamentos [Admin]\n"
    response += "   Shows all users' payments, with page navigation.\n\n"
    response += "!testar_lembrete [Admin]\n"
    response += "   Sends test reminders to users with the current month unpaid.\n\n"
    response += "!definir_canal_lembrete [Admin]\n"
    response += "   Sets the channel for reminders and summaries.\n\n"
    response += "!definir_canal_comandos [Admin]\n"
    response += "   Sets the channel where commands can be used.\n\n"
    response += "!definir_canal_confirmacao [Admin]\n"
    response += "   Sets the channel for payment confirmations.\n\n"
    response += "!ajuda\n"
    response += "   Shows this command list.\n"
    response += "```"
    await ctx.send(response)
