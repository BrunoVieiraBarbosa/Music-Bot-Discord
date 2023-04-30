import json
from discord.ext import commands
from discord.ext.commands import has_permissions
from discord.utils import get


class Functions(commands.Cog):
    def __init__(self, client):
        self.client = client


    @commands.command(pass_context=True)
    async def ping(self, ctx):
        await ctx.send(f'Ping: {round(self.client.latency, 2)}')


    @commands.command(pass_context=True, help="Exclui as mensagens de um canal de texto.")
    @has_permissions(manage_channels=True, manage_messages=True)
    async def clear(self, ctx, user=None, amount=None):
        info_ = {'user': None, 'amount':None}

        if (user != None):
            if (user.startswith('<@') and user.endswith('>')):
                user = await commands.MemberConverter().convert(ctx, user)
                info_['user'] = user
                info_['amount'] = '0' if amount == None else amount
            else:
                info_['amount'] = user
        else:
            info_['amount'] = '0'
        
        if not info_["amount"].isdigit():
            return await ctx.send("```A informação passada não é um numero inteiro```")

        delete_ = int(info_["amount"]) if int(info_["amount"]) > 0 else 10000

        if (info_["user"] != None):
            limit = 10_000 if delete_ < 10_000 else delete_ * 2
            count = 0
            async for message in ctx.channel.history(limit=limit):
                if message.author == info_["user"]:
                    delete_ -= 1
                count += 1
                if delete_ == 0:
                    break

            deleted_now = await ctx.channel.purge(limit=count, check=lambda m: m.author == info_['user'])
        else:
            deleted_now = await ctx.channel.purge(limit=delete_)

        if len(deleted_now) >= 1:
            return await ctx.channel.send(
                f'{len(deleted_now)} mensage{"m" if len(deleted_now) == 1 else "ns"} deletada{"" if len(deleted_now) == 1 else "s"}.'
                )

        return await ctx.channel.send(f'```Nenhuma mensagem deletada.```')


    @commands.command(pass_context=True, help="Troca o prefixo do servidor")
    @has_permissions(ban_members=True, kick_members=True, manage_channels=True, manage_roles=True)
    async def changeprefix(self, ctx, *kwargs):
        if len(kwargs) > 0:
            if not kwargs[0].isdigit():
                with open('prefix.json', 'r') as file:
                    prefixes = json.load(file)

                prefix = kwargs[0].replace('\'', '').replace('\"', "")
                prefixes[str(ctx.guild.id)] = prefix

                with open('prefix.json', 'w') as file:
                    json.dump(prefixes, file, indent=4)

                return await ctx.send(f"```Novo prefixo: {prefix}```")
        else:
            return await ctx.send("```Você não mandou o novo prefixo.```")


async def setup(client):
    await client.add_cog(Functions(client))
