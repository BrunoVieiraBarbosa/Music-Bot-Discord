from discord.ext import commands
from discord.utils import get


class Browser(commands.Cog):
    def __init__(self, client):
        self.client = client


    @commands.command(pass_context=True) 
    async def join(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        author_channel = ctx.author.voice
        
        if not author_channel:
            return await ctx.send("```Você não está em um canal de audio.```")
        author_channel = author_channel.channel

        if (voice == None):
            return await author_channel.connect()
        
        if (voice.channel == author_channel):
            return await ctx.send("```O bot ja está conectado no canal de audio.```")
        elif (voice.is_playing() or voice.is_paused()):
            return await ctx.send('```O bot esta tocando uma musica em outro canal de audio.```')
        elif (not voice.is_playing() and not voice.is_paused()):
            return await author_channel.connect()


    @commands.command(pass_context=True)
    async def joinforce(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        author_channel = ctx.author.voice
        
        if (author_channel == None):
            return await ctx.send("```Você não está em um canal de audio.```")
        author_channel = author_channel.channel

        if (voice == None):
            return await author_channel.connect()
        elif (voice.channel == author_channel):
            return await ctx.send("```O bot ja está conectado no canal de audio.```")
        elif (voice.is_playing() or voice.is_paused()):
            await voice.move_to(author_channel)
        else:
            await voice.disconnect()
            return await author_channel.connect()


    @commands.command(pass_context=True)
    async def leave(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        author_channel = ctx.author.voice
        
        if (voice == None):
            return await ctx.send("```O bot não esta conectado em nenhum canal de audio```")
        
        if (author_channel == None):
            return await ctx.send("```Você não está no mesmo canal de audio do bot.```")
        author_channel = author_channel.channel

        if (voice.is_playing() or voice.is_paused()):
            return await ctx.send("```Pare a musica antes de pedir para o bot sair.```")
        else:
            return await voice.disconnect()



async def setup(client):
    await client.add_cog(Browser(client))