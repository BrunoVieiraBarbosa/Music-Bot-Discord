from discord.ext import commands
from discord.utils import get


class Browser(commands.Cog):
    def __init__(self, client):
        self.client = client


    @commands.command(pass_context=True) 
    async def join(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        #Verifica se o usuario está em um canal de audio
        if not ctx.author.voice:
            return await ctx.send("```Você não está em um canal de audio.```")

        #Verifica se o bot está em canal de audio, caso não esteja ele se conecta ao canal do usuario
        if (voice == None):
            return await ctx.author.voice.channel.connect()
        
        #Valida se está no mesmo canal de audio do usuario
        if (voice.channel == ctx.author.voice.channel):
            return await ctx.send("```Já estou conectado no canal de audio.```")

        #Valida se o bot está tocando alguma musica em outro canal
        elif (voice.is_playing() or voice.is_paused()):
            return await ctx.send('```Estou tocando uma musica em outro canal de audio.```')

        return await voice.move_to(ctx.author.voice.channel)


    @commands.command(pass_context=True)
    async def leave(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        #Verifica se o usuario está em um canal de audio
        if not ctx.author.voice:
            return await ctx.send("```Você não está no mesmo canal de audio que eu.```")

        #Verifica se o bot está em canal de audio
        if (voice == None):
            return await ctx.send("```Não estou em nenhum canal de audio```")

        #Valida se o bot está tocando alguma musica em outro canal
        if (voice.is_playing() or voice.is_paused()):
            return await ctx.send("```Pare a musica antes de pedir para eu sair.```")

        return await voice.disconnect()



async def setup(client):
    await client.add_cog(Browser(client))