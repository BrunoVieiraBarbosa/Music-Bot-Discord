from client import Client
import discord, credentials, asyncio


async def main():
    client = Client(command_prefix = Client.get_prefix, intents=discord.Intents.all())
    await client.read_cogs()
    await client.start(credentials.TOKEN)
    

if (__name__ == "__main__"):
    asyncio.run(main())