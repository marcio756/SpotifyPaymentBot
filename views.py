import discord
from discord.ui import Button, View
from utils import load_payments, save_payments, set_payment_status


class ConfirmPaymentView(View):

    def __init__(self, user_id, year, months):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.year = year
        self.months = months

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.green)
    async def confirm_button(self, interaction: discord.Interaction,
                             button: discord.Button):
        """Confirms a user's payment."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Only administrators can confirm payments!")
            return
        payments = load_payments()
        user_id_str = str(self.user_id)
        confirmation_channel = interaction.client.get_channel(
            interaction.client.confirmation_channel_id)
        commands_channel = interaction.client.get_channel(
            interaction.client.commands_channel_id)
        for month in self.months:
            set_payment_status(payments, user_id_str, self.year, month, True)
            if 'pending_payments' in payments and user_id_str in payments[
                    'pending_payments']:
                if self.year in payments['pending_payments'][user_id_str]:
                    if month in payments['pending_payments'][user_id_str][
                            self.year]:
                        # Update the confirmation channel message
                        confirmation_message_id = payments['pending_payments'][
                            user_id_str][self.year][month].get(
                                'confirmation_message_id')
                        if confirmation_message_id and confirmation_channel:
                            try:
                                confirmation_message = await confirmation_channel.fetch_message(
                                    confirmation_message_id)
                                await confirmation_message.edit(
                                    content=
                                    f"Payment for {month.capitalize()}/{self.year} accepted by admin.",
                                    view=None)
                            except discord.errors.NotFound:
                                print(
                                    f"Confirmation message {confirmation_message_id} not found."
                                )
                        # Update the commands channel response message
                        response_message_id = payments['pending_payments'][
                            user_id_str][self.year][month].get(
                                'response_message_id')
                        if response_message_id and commands_channel:
                            try:
                                response_message = await commands_channel.fetch_message(
                                    response_message_id)
                                await response_message.edit(
                                    content=
                                    f"Payment intention for {month.capitalize()} registered! Admin accepted the confirmation."
                                )
                            except discord.errors.NotFound:
                                print(
                                    f"Response message {response_message_id} not found."
                                )
                        # Remove the pending payment
                        del payments['pending_payments'][user_id_str][
                            self.year][month]
                        if not payments['pending_payments'][user_id_str][
                                self.year]:
                            del payments['pending_payments'][user_id_str][
                                self.year]
                        if not payments['pending_payments'][user_id_str]:
                            del payments['pending_payments'][user_id_str]
        save_payments(payments, interaction.client.lembrete_channel_id,
                      interaction.client.commands_channel_id,
                      interaction.client.confirmation_channel_id)
        user = await interaction.client.fetch_user(int(user_id_str))
        await interaction.response.edit_message(
            content=
            f"Payment for {', '.join(self.months).capitalize()}/{self.year} from {user.mention} confirmed!",
            view=None)

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny_button(self, interaction: discord.Interaction,
                          button: discord.Button):
        """Denies a user's payment."""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "Only administrators can deny payments!")
            return
        payments = load_payments()
        user_id_str = str(self.user_id)
        confirmation_channel = interaction.client.get_channel(
            interaction.client.confirmation_channel_id)
        commands_channel = interaction.client.get_channel(
            interaction.client.commands_channel_id)
        if 'pending_payments' in payments and user_id_str in payments[
                'pending_payments']:
            if self.year in payments['pending_payments'][user_id_str]:
                for month in self.months:
                    if month in payments['pending_payments'][user_id_str][
                            self.year]:
                        # Update the confirmation channel message
                        confirmation_message_id = payments['pending_payments'][
                            user_id_str][self.year][month].get(
                                'confirmation_message_id')
                        if confirmation_message_id and confirmation_channel:
                            try:
                                confirmation_message = await confirmation_channel.fetch_message(
                                    confirmation_message_id)
                                await confirmation_message.edit(
                                    content=
                                    f"Payment for {month.capitalize()}/{self.year} denied by admin.",
                                    view=None)
                            except discord.errors.NotFound:
                                print(
                                    f"Confirmation message {confirmation_message_id} not found."
                                )
                        # Update the commands channel response message
                        response_message_id = payments['pending_payments'][
                            user_id_str][self.year][month].get(
                                'response_message_id')
                        if response_message_id and commands_channel:
                            try:
                                response_message = await commands_channel.fetch_message(
                                    response_message_id)
                                await response_message.edit(
                                    content=
                                    f"Payment intention for {month.capitalize()} registered! Admin denied the confirmation."
                                )
                            except discord.errors.NotFound:
                                print(
                                    f"Response message {response_message_id} not found."
                                )
                        # Remove the pending payment
                        del payments['pending_payments'][user_id_str][
                            self.year][month]
                if not payments['pending_payments'][user_id_str][self.year]:
                    del payments['pending_payments'][user_id_str][self.year]
                if not payments['pending_payments'][user_id_str]:
                    del payments['pending_payments'][user_id_str]
        save_payments(payments, interaction.client.lembrete_channel_id,
                      interaction.client.commands_channel_id,
                      interaction.client.confirmation_channel_id)
        user = await interaction.client.fetch_user(int(user_id_str))
        await interaction.response.edit_message(
            content=
            f"Payment for {', '.join(self.months).capitalize()}/{self.year} from {user.mention} denied.",
            view=None)
