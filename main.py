from client import Client
import discord


if (__name__ == "__main__"):
    client = Client(command_prefix = Client.get_prefix, intents=discord.Intents.all())

    token = 'YOUR-TOKEN'
    client.run(token)