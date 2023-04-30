from discord.ext import commands
from discord.ext.commands.help import DefaultHelpCommand
import json, discord, os


class Client(commands.Bot):
    def __init__(self, command_prefix, help_command=DefaultHelpCommand(), description=None, **options) -> None:
        super().__init__(command_prefix, help_command=help_command, description=description, **options)


    @staticmethod
    async def get_prefix(message) -> str:
        #Verifica se o arquivo de prefixo existe, caso não exista é criado.
        if 'prefix.json' not in os.listdir('.'):
            with open('prefix.json', 'w') as file:
                file.write('{}')

        with open('prefix.json', 'r') as file:
            prefixes = json.load(file)

        #Verifica se o server do usuario está no arquivo, caso não esteja é registrado.
        if str(message.guild.id) not in prefixes:
            prefixes[str(message.guild.id)] = ">"
            with open('prefix.json', 'w') as file:
                json.dump(prefixes, file, indent=4)

        #Retorna o prefixo do server
        return prefixes[str(message.guild.id)]


    async def read_cogs(self) -> None:
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f"cogs.{filename[:-3]}")


    async def on_guild_join(guild) -> None:
        if 'prefix.json' not in os.listdir('.'):
            prefixes = {}
        else:
            with open('prefix.json', 'r') as file:
                prefixes = json.load(file)

        prefixes[str(guild.id)] = ">"

        with open('prefix.json', 'w') as file:
            json.dump(prefixes, file, indent=4)


    async def on_guild_remove(guild) -> None:
        if 'prefix.json' not in os.listdir('.'):
            return

        with open('prefix.json', 'r') as file:
            prefixes = json.load(file)

        prefixes.pop(str(guild.id))

        with open('prefix.json', 'w') as file:
            json.dump(prefixes, file, indent=4)


    async def on_ready(self) -> None:
        print('Logged!')


    async def on_command_error(self, ctx, error):
        #Tratando alguns erros
        if isinstance(error, commands.errors.MemberNotFound):
            return await ctx.send("```Usuario mencionado não existe nesse servidor.```")
        elif isinstance(error, commands.errors.CommandNotFound):
            return await ctx.send(f"```Comando não encontrado, digite {await self.get_prefix(ctx.message)}help.```")
        elif isinstance(error, commands.errors.MissingPermissions):
            return await ctx.send("```Você não tem permissão para realizar esse comando.```")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            return await ctx.send("```É necessario enviar todos os argumentos.```")
        elif isinstance(error, commands.errors.ExpectedClosingQuoteError):
            return await ctx.send("```Você enviou um ou mais caracteres invalidos.```")
        elif isinstance(error, commands.errors.CommandInvokeError):
            return
        else:
            print(type(error))
            print(error)


    async def who_i_am(self, message):
        prefix_ = await Client.get_prefix(message)
        msembed = discord.Embed(title=f"Eu sou o {self.user.name}")
        msembed.add_field(name=f"{prefix_}", value=f"\'{prefix_}\' é o seu prefixo.", inline=False)
        msembed.add_field(name=f"{prefix_}help", value="Esse comando ira te mostrar todos os comandos que tenho.", inline=False)
        return await message.channel.send(embed=msembed)


    async def on_message(self, message):
        if message.content.startswith(f'<@{self.user.id}>'):
            return await self.who_i_am(message)
        await self.process_commands(message)
