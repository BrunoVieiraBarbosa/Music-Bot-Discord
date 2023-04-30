from datetime import datetime, timedelta
from discord.ext import commands, tasks
from discord.utils import get
from discord import FFmpegPCMAudio
from youtube_dl import YoutubeDL
import discord, time, re, requests, asyncio


class MusicController(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.actual_page, self.playlist = {}, {}
        self.playing, self.play_again = {}, {}
        self.time_playing, self.cursor = {}, {}
        self.emoji, self.message_page = {}, {}
        self.COR = 0xF7FE2E
        self.ydl_option = {'format': 'bestaudio/best', 'noplaylist':'True', 'quiet':'True'}
        self.ffmpeg_options = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}
        self.switch_music.start()


    def next_music(self, ctx):
        self.playing[ctx.guild.id] = False


    @tasks.loop(seconds=2)
    async def switch_music(self):
        for guild in self.playlist.keys():
            if not self.playing[guild] and (self.cursor.get(guild) != None):
                if  self.cursor[guild]['locate'] < len(self.playlist[guild])-1:
                    if self.cursor[guild].get('ctx') != None:
                        if (self.play_again[guild] == 0):
                            self.cursor[guild]['locate'] += 1

                        start_play = await self.play_now(self.cursor[guild]['ctx'])
                        if start_play:
                            msg = await self.embed_message_update_music(self.cursor[guild]['ctx'])
                            await self.update_player_reaction(guild, msg)
                        elif (self.play_again[guild] == 0):
                            self.cursor[guild]['locate'] -= 1
                        
                        if (self.play_again[guild] == 1) and start_play:
                            self.play_again[guild] = 0

                elif self.cursor[guild]['locate'] == len(self.playlist[guild])-1:
                    if self.cursor[guild].get('ctx') != None:

                        if (self.play_again[guild] == 1):
                            self.play_again[guild] = 0
                            if await self.play_now(self.cursor[guild]['ctx']):
                                msg = await self.embed_message_update_music(self.cursor[guild]['ctx'])
                                await self.update_player_reaction(guild, msg)

                        elif (self.play_again[guild] > 1):
                            if await self.play_now(self.cursor[guild]['ctx']):
                                msg = await self.embed_message_update_music(self.cursor[guild]['ctx'])
                                await self.update_player_reaction(guild, msg)

                self.playlist[guild] = self.playlist[guild][0 if self.cursor[guild]['locate']-2 <= 0 else self.cursor[guild]['locate']-2:].copy()
                self.cursor[guild]['locate'] -= 0 if self.cursor[guild]['locate']-2 <= 0 else self.cursor[guild]['locate']-2

                if not self.playing[guild] and (self.cursor[guild]['locate'] == len(self.playlist[guild])-1):
                    self.playlist[guild] = []
                    self.cursor[guild]['locate'] = -1
                    self.play_again[guild] = 0


    async def get_playlist_links(self, url: str):
        page_text = requests.get(url).text
        parser = re.compile(r"watch\?v=\S+?list=")
        playlist = set(re.findall(parser, page_text))
        return list(
            map(
            (lambda x: "https://www.youtube.com/" + x.replace("\\u0026list=", "")), playlist
            )
        )


    async def get_url(self, url):
        try:    
            with YoutubeDL(self.ydl_option) as ydl:
                if url.startswith("https://") or url.startswith("http://"):
                    info = ydl.extract_info(url, download=False)
                else:
                    info = ydl.extract_info(f'ytsearch:{url}', download=False)['entries'][0]
            URL = info['formats'][0]['url']
            return info, URL
        except Exception:
            return False


    async def embed_message_update_music(self, ctx):
        user = self.playlist[ctx.guild.id][self.cursor[ctx.guild.id]['locate']]['user']
        metadata = self.playlist[ctx.guild.id][self.cursor[ctx.guild.id]['locate']]['metadata'].copy()

        metadata["view_count"] = f'{metadata["view_count"]:,}'.replace(',', '.')
        metadata["like_count"] = f'{metadata["like_count"]:,}'.replace(',', '.')

        if "dislike_count" in metadata.keys():
            metadata["dislike_count"] = f'{metadata["dislike_count"]:,}'.replace(',', '.')
        else:
            metadata["dislike_count"] = 0

        metadata["duration"] = datetime.strptime(timedelta(seconds=metadata["duration"]).__str__(), '%H:%M:%S').strftime('%H:%M:%S')
        metadata["upload_date"] = datetime.strptime(metadata["upload_date"], '%Y%m%d').strftime('%d-%m-%Y')
        
        if self.time_playing[ctx.guild.id]['time'] != None:
            time_ = int((time.time() - self.time_playing[ctx.guild.id]['time']) + self.time_playing[ctx.guild.id]['total'])
        else:
            time_ = int(self.time_playing[ctx.guild.id]['total'])

        time_ = datetime.strptime(timedelta(seconds=time_).__str__(), '%H:%M:%S').strftime('%H:%M:%S')


        mscemb = discord.Embed(
            title=f"Pedido por {user.name}",
            color=self.COR
            )
        mscemb.set_image(url=metadata['thumbnail'])
        mscemb.add_field(name="Nome:", value=f"`{metadata['title']}`")
        mscemb.add_field(name="Visualizações:", value=f"`{metadata['view_count']}`")
        mscemb.add_field(name="Enviado em:", value=f"`{metadata['upload_date']}`")
        mscemb.add_field(name="Enviado por:", value=f"`{metadata['uploader']}`")
        mscemb.add_field(name="Duraçao:", value=f"`{metadata['duration']}`")
        mscemb.add_field(name="Tempo decorrido:", value=f"`{time_}`")
        mscemb.add_field(name="Likes:", value=f"`{metadata['like_count']}`")
        mscemb.add_field(name="dislikes:", value=f"`{metadata['dislike_count']}`")
        mscemb.add_field(name="link:", value=f"[Youtube]({metadata['webpage_url']})")

        mscemb.set_image(url=metadata['thumbnail'])
        return await ctx.send(embed = mscemb)


    async def embed_message_update_queue(self, ctx, metadata, pos_queue):
        metadata["duration"] = datetime.strptime(timedelta(seconds=metadata["duration"]).__str__(), '%H:%M:%S').strftime('%H:%M:%S')

        mscemb = discord.Embed(
            title=f"Musica adicionada por {ctx.author.name}",
            color=self.COR,
            description=f"{pos_queue}° posição na fila."
            )
        mscemb.set_image(url=metadata['thumbnail'])
        mscemb.add_field(name="Nome:", value=f"`{metadata['title']}`")
        mscemb.add_field(name="Duraçao:", value=f"`{metadata['duration']}`")

        return await ctx.send(embed = mscemb)
    

    async def embed_message_send(self, ctx, description):
        mscembed = discord.Embed(title="\n",
                                color=self.COR,
                                description=description)
        return await ctx.send(embed=mscembed)


    async def play_now(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if voice == None:
            return False
        if not voice.is_connected():
            return False

        self.playing[ctx.guild.id] = True

        self.time_playing[ctx.guild.id]['time'] = time.time()
        self.time_playing[ctx.guild.id]['total'] = 0

        URL = self.playlist[ctx.guild.id][self.cursor[ctx.guild.id]['locate']]['url']

        voice.play(FFmpegPCMAudio(URL, **self.ffmpeg_options), after = lambda _: self.next_music(ctx))
        voice.source = discord.PCMVolumeTransformer(voice.source)
        voice.source.volume = 1.0

        self.cursor[ctx.guild.id]['ctx'] = ctx
        return True


    async def bot_on_channel(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        if voice:
            return True
        return False


    async def bot_same_channel(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        if voice and ctx.author.voice:
            return voice.channel == ctx.author.voice.channel
        return False
    

    async def user_on_channel(self, ctx):
        if ctx.author.voice:
            return True
        return False


    async def add_player_reaction(self, msg):
        for x in ("⏮️", "⏸️", "▶️", "⏭️", "⏹️", "🔁"):
            await msg.add_reaction(x)
    

    async def add_queue_reaction(self, msg):
        await msg.add_reaction("⬅️")
        await msg.add_reaction("➡️")


    async def remove_reaction(self, msg):
        try:
            await msg.clear_reactions()
        except discord.errors.NotFound:
            pass


    async def update_player_reaction(self, guild_id, new_msg):
        if self.emoji.get(guild_id) == None:
            return
        if (self.emoji[guild_id]['player'] != None):
            await self.remove_reaction(self.emoji[guild_id]['player'])
        await self.add_player_reaction(new_msg)
        self.emoji[guild_id]['player'] = new_msg
    

    async def update_queue_reaction(self, guild_id, new_msg):
        if self.emoji.get(guild_id) == None:
            return
        if (self.emoji[guild_id]['queue'] != None):
            await self.remove_reaction(self.emoji[guild_id]['queue'])
        await self.add_queue_reaction(new_msg)
        self.emoji[guild_id]['queue'] = new_msg


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        async def on_same_channel(self, guild, author_voice):
            voice = get(self.client.voice_clients, guild=guild)
            if voice and author_voice:
                return voice.channel == author_voice.channel

        if (user.id != self.client.user.id):
            if reaction.me:
                #Controles da fila
                if (reaction.emoji == "⬅️"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        self.actual_page[user.guild.id]['page'] -= 1
                        msg = await self.fila(self.cursor[user.guild.id]['ctx'], self.actual_page[user.guild.id])
                        if (msg != None):
                            await asyncio.sleep(3)
                            await msg.delete()

                elif (reaction.emoji == "➡️"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        self.actual_page[user.guild.id]['page'] += 1
                        msg = await self.fila(self.cursor[user.guild.id]['ctx'], self.actual_page[user.guild.id])
                        if (msg != None):
                            await asyncio.sleep(3)
                            await msg.delete()


                #Player de musica
                if (reaction.emoji == "⏮️"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        msg = await self.back(self.cursor[user.guild.id]['ctx'])
                        await asyncio.sleep(3)
                        await msg.delete()

                elif (reaction.emoji == "⏸️"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        msg = await self.pause(self.cursor[user.guild.id]['ctx'])
                        await asyncio.sleep(3)
                        await msg.delete()

                elif (reaction.emoji == "▶️"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        msg = await self.resume(self.cursor[user.guild.id]['ctx'])
                        await asyncio.sleep(3)
                        await msg.delete()

                elif (reaction.emoji == "⏭️"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        msg = await self.skip(self.cursor[user.guild.id]['ctx'])
                        await asyncio.sleep(3)
                        await msg.delete()
                
                elif (reaction.emoji == "⏹️"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        msg = await self.stop(self.cursor[user.guild.id]['ctx'])
                        await asyncio.sleep(3)
                        await msg.delete()
                
                elif (reaction.emoji == "🔁"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        msg = await self.repeat(self.cursor[user.guild.id]['ctx'])
                        await asyncio.sleep(3)
                        await msg.delete()


    #Comandos do Usuario
    @commands.command(pass_content=True, help="[<prefix>play <Nome ou link da musica>] - Toca um musica ou a adiciona na lista.")
    async def play(self, ctx, *kwargs):
        if kwargs:
            if not await self.bot_same_channel(ctx):
                if not await self.bot_on_channel(ctx):
                    if ctx.author.voice:
                        await ctx.author.voice.channel.connect()
                    else:
                        return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")
                else:
                    voice = get(self.client.voice_clients, guild=ctx.guild)
                    if voice:
                        if voice.is_playing() or voice.is_paused():
                            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")
                    elif ctx.author.voice:
                        await ctx.author.voice.channel.connect()
                    else:
                        return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")

            if self.playlist.get(ctx.guild.id) == None:
                self.playlist[ctx.guild.id] = []
            if self.playing.get(ctx.guild.id) == None:
                self.playing[ctx.guild.id] = False
            if self.cursor.get(ctx.guild.id) == None:
                self.cursor[ctx.guild.id] = {'locate': -1, 'ctx': ctx}
            if self.time_playing.get(ctx.guild.id) == None:
                self.time_playing[ctx.guild.id] = {'time': None, 'total': 0}
            if self.play_again.get(ctx.guild.id) == None:
                self.play_again[ctx.guild.id] = 0
            if self.emoji.get(ctx.guild.id) == None:
                self.emoji[ctx.guild.id] = {'player': None, 'queue': None}


            if kwargs[-1].isdigit() and ('https://www.youtube.com/' in kwargs[0]):
                url = ' '.join(kwargs[:-1])
                only_this = int(kwargs[-1])
            elif ('https://www.youtube.com/' in kwargs[0]):
                url = kwargs[0]
                only_this = 0
            else:
                url = ' '.join(kwargs)
                only_this = 0

            if url.startswith('https://www.youtube.com/'):
                #Playlist
                if ('&list=' in url and only_this != 0):
                    url = f'https://www.youtube.com/playlist?list={url[url.index("&list=")+6:]}'

                #Playlist
                if ('playlist?list=' in url):
                    links = await self.get_playlist_links(url)
                    links = links[:50]
                    msg = await ctx.send(f"```Carregando {len(links)} musica{'s' if len(links) > 1 else ''}.```")
                    for link in links:
                        data = await self.get_url(link)
                        if data:
                            plural = 's' if links.index(link)+1 > 1 else ''
                            await msg.edit(content=f"```{links.index(link)+1} musica{plural} adicionada{plural} ```")
                            self.playlist[ctx.guild.id].append({
                                        'url': data[1], 'metadata': data[0], 'user': ctx.author})

                #Musica individual
                else:
                    data = await self.get_url(url)
                    if not data:
                        return await self.embed_message_send(ctx, "Musica não encontrada.")
                    self.playlist[ctx.guild.id].append({
                                        'url': data[1], 'metadata': data[0].copy(), 'user': ctx.author})
                    pos = (len(self.playlist[ctx.guild.id])-1) - self.cursor[ctx.guild.id]['locate']
                    if (pos > 0) and (self.cursor[ctx.guild.id]['locate'] >= 0):
                        await self.embed_message_update_queue(ctx, data[0].copy(), pos)
                    

            else:
                data = await self.get_url(url)
                if not data:
                    return await self.embed_message_send(ctx, "Musica não encontrada.")
                self.playlist[ctx.guild.id].append({
                                    'url': data[1], 'metadata': data[0].copy(), 'user': ctx.author})
                pos = (len(self.playlist[ctx.guild.id])-1) - self.cursor[ctx.guild.id]['locate']
                if (pos > 0) and (self.cursor[ctx.guild.id]['locate'] >= 0):
                    await self.embed_message_update_queue(ctx, data[0].copy(), pos)


    @commands.command(pass_content=True, help="Reproduz a musica novamente quando acabar.")
    async def repeat(self, ctx):
        if not await self.bot_on_channel(ctx):
            return await self.embed_message_send(ctx, "O bot não está em nenhum canal de audio.")

        if not await self.bot_same_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal de audio do bot.")

        if not await self.user_on_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")

        if (self.play_again.get(ctx.guild.id) == None) or (self.playing.get(ctx.guild.id) == None) or (self.playing[ctx.guild.id] == False):
            return await self.embed_message_send(ctx, "O bot não está tocando nenhuma musica.")

        if (self.play_again[ctx.guild.id] == 0):
            self.play_again[ctx.guild.id] = 1
            return await self.embed_message_send(ctx, "O bot ira repitir uma unica vez essa musica.")

        elif (self.play_again[ctx.guild.id] == 1):
            self.play_again[ctx.guild.id] = 2
            return await self.embed_message_send(ctx, "O bot ficará repitindo essa musica.")

        else:
            self.play_again[ctx.guild.id] = 0
            return await self.embed_message_send(ctx, "O bot não ira repitir essa musica.")


    @commands.command(pass_content=True, help="Reproduz a musica anterior")
    async def back(self, ctx):
        if not await self.bot_on_channel(ctx):
            return await self.embed_message_send(ctx, "O bot não está em nenhum canal de audio.")
        if not await self.bot_same_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal de audio do bot.")
        if not await self.user_on_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")
        if (self.playing.get(ctx.guild.id) == None) or (self.playing[ctx.guild.id] == False):
            return await self.embed_message_send(ctx, "O bot não está tocando nenhuma musica.")

        voice = get(self.client.voice_clients, guild=ctx.guild)

        if (self.cursor[ctx.guild.id]['locate'] - 2 >= -1) and (self.play_again[ctx.guild.id] == 0):
            self.cursor[ctx.guild.id]['locate'] -= 2
            voice.stop()
            return await self.embed_message_send(ctx, "Reproduzindo musica anterior.")

        elif (self.cursor[ctx.guild.id]['locate'] - 1 >= 0) and (self.play_again[ctx.guild.id] >= 1):
            self.cursor[ctx.guild.id]['locate'] -= 1
            voice.stop()
            return await self.embed_message_send(ctx, "Reproduzindo musica anterior.")
        else:
            return await self.embed_message_send(ctx, "Não tem musicas anteriores.")


    @commands.command(pass_context=True, help="Exibe informações da musica que esta sendo tocada.")
    async def now(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        if (voice == None):
            return await self.embed_message_send(ctx, "Não tem musica tocando.")
        elif (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")

        if self.playing.get(ctx.guild.id) != None:
            if not self.playing[ctx.guild.id]:
                return await self.embed_message_send(ctx, "Não tem musica tocando.")
            msg = await self.embed_message_update_music(ctx)
            await self.update_player_reaction(ctx.guild.id, msg)
        else:
            return await self.embed_message_send(ctx, "Não tem musica tocando.")


    @commands.command(pass_content=True, help="Pausa a musica atual.")
    async def pause(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        author_channel = ctx.author.voice

        if (author_channel == None):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")
        author_channel = author_channel.channel

        if (voice == None):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")
        elif (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")
        elif voice.is_paused():
            return await self.embed_message_send(ctx, "A musica ja está pausada.")

        if (author_channel != voice.channel):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal de audio do Bot.")

        time_ = time.time() - self.time_playing[ctx.guild.id]['time']
        self.time_playing[ctx.guild.id]['total'] += time_
        self.time_playing[ctx.guild.id]['time'] = None
        voice.pause()

        mscpause = discord.Embed(title="\n", color=self.COR, description="Musica pausada com sucesso!")
        return await ctx.send(embed=mscpause)


    @commands.command(pass_context=True, help="Volta a tocar a musica.")
    async def resume(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        author_channel = ctx.author.voice

        if (author_channel == None):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")
        author_channel = author_channel.channel

        if (ctx.guild.id not in self.playing):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")
        
        if (voice == None):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")
        elif (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")
        elif voice.is_playing():
            return await self.embed_message_send(ctx, "A musica não está pausada.")

        if (author_channel != voice.channel):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal de audio do Bot.")

        self.time_playing[ctx.guild.id]['time'] = time.time()
        voice.resume()

        mscresume = discord.Embed(title="\n", color=self.COR, description="Voltando a tocar a musica!")
        return await ctx.send(embed=mscresume)


    @commands.command(pass_context=True, help="Para de tocar e exclui todas as musicas da fila atual.")
    async def stop(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        author_channel = ctx.author.voice

        if (author_channel == None):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")
        author_channel = author_channel.channel

        if (voice == None):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")
        elif (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")

        if (author_channel != voice.channel):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal de audio do Bot.")

        mscpause = discord.Embed( title="\n", color=self.COR, 
                                description="Musica parada e todas as musicas da fila atual foram excuidas!")

        voice.stop()
        self.playlist[ctx.guild.id] = []
        self.cursor[ctx.guild.id]['locate'] = -1
        self.play_again[ctx.guild.id] = 0
        return await ctx.send(embed=mscpause)


    @commands.command(pass_context=True, help="Pula para a proxima musica da fila.")
    async def skip(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        author_channel = ctx.author.voice

        if (author_channel == None):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")
        author_channel = author_channel.channel

        if (voice == None):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")
        elif (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")

        if (author_channel != voice.channel):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal de audio do Bot.")

        if self.playlist.get(ctx.guild.id) == None:
            return await self.embed_message_send(ctx, "Não tem musicas na lista.")
        elif (len(self.playlist[ctx.guild.id]) > 0):
            if self.cursor[ctx.guild.id]['locate'] == len(self.playlist[ctx.guild.id])-1:
                if self.play_again[ctx.guild.id] >= 1:
                    self.play_again[ctx.guild.id] = 0
                description = "Não tem musicas na lista."

            elif self.cursor[ctx.guild.id]['locate'] < len(self.playlist[ctx.guild.id])-1:
                if self.play_again[ctx.guild.id] >= 1:
                    self.play_again[ctx.guild.id] = 0
                description = "Reproduzindo a proxima musica!"

            mscskip = discord.Embed(title="\n", color=self.COR, description=description)
            voice.stop()
            return await ctx.send(embed=mscskip)
        else:
            return await self.embed_message_send(ctx, "Não tem mais musicas na lista.")


    @commands.command(pass_context=True, help="Aumenta e diminui o volume do audio.")
    async def vol(self, ctx, volume: str = None):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        author_channel = ctx.author.voice

        if (author_channel == None):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")
        author_channel = author_channel.channel

        if (voice == None):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")
        elif (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")

        if (author_channel != voice.channel):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal de audio do Bot.")

        if (volume == ""):
            return await self.embed_message_send(ctx, f"Volume atual: {int(voice.source.volume*100)}")

        if (not volume.isdigit()):
            return await self.embed_message_send(ctx, "Certifique de inserir apenas numeros inteiros apos o comando")
        
        volume = float(volume) / 100
        
        if (volume <= 1000.0):
            if (voice.source.volume == volume):
                text = f"O volume continua {int(volume*100)}%"
            else:
                text = f"{'Aumentando' if voice.source.volume < volume else 'Diminuindo'} o volume para {int(volume*100)}%"
            voice.source.volume = volume

            mscresume = discord.Embed(title="Volume", color=self.COR, description=text)

            return await ctx.send(embed=mscresume)
        else:
            return await self.embed_message_send(ctx, f"Volume maximo aceito: {int(1000*100)}")


    @commands.command(pass_context=True, help="Lista cada musica da fila.")
    async def fila(self, ctx, *kwargs):
        if self.playlist.get(ctx.guild.id) == None:
            return await self.embed_message_send(ctx, "Não tem musicas na fila.")
        
        if (len(self.playlist[ctx.guild.id]) == 0):
            return await self.embed_message_send(ctx, "Não tem musicas na fila.")

        if self.actual_page.get(ctx.guild.id) == None:
            self.actual_page[ctx.guild.id] = {'msg': None, 'page': 0}

        page = 1
        msg_reuse = False
    
        if len(kwargs) > 0 and kwargs != (self.actual_page[ctx.guild.id], ):
            if kwargs[0].isdigit():
                page = int(kwargs[0])
        elif kwargs == (self.actual_page[ctx.guild.id], ):
            msg_reuse = True
            page = self.actual_page[ctx.guild.id]['page']
        
        page = 1 if page <= 0 else page
        
        self.actual_page[ctx.guild.id]['page'] = page
        
        start = self.cursor[ctx.guild.id]['locate'] + 1 + ((page-1) * 10)
        pos = self.cursor[ctx.guild.id]['locate']
        end = start + 10

        if (start > len(self.playlist[ctx.guild.id])-1):
            self.actual_page[ctx.guild.id]['page'] -= 1
            return await self.embed_message_send(ctx, f'Não tem musicas para listar na {page}° pagina.')
        
        metadata = self.playlist[ctx.guild.id][self.cursor[ctx.guild.id]['locate']]['metadata']
        author = self.playlist[ctx.guild.id][self.cursor[ctx.guild.id]['locate']]['user']
        text = f"`Tocando Agora`:\n[{metadata['title']}]({metadata['webpage_url']}) - `Pedido por: {author.name}`\n\nAbaixo as musicas da lista"

        mscemb = discord.Embed(title=f"Fila - {page}° pagina", description=text, color=self.COR)

        for i, music in enumerate(self.playlist[ctx.guild.id][start:], start):
            metadata = music['metadata']
            author = music['user']
            mscemb.add_field(name=f"{i-pos}° - {metadata['title']}", value=f'Adicionado por {author.name}\n', inline=False)

            if (i+1 == end):
                break

        if msg_reuse:
            await self.actual_page[ctx.guild.id]['msg'].edit(embed=mscemb)
        else:
            self.actual_page[ctx.guild.id]['msg'] = await ctx.send(embed=mscemb)

        return await self.update_queue_reaction(ctx.guild.id, self.actual_page[ctx.guild.id]['msg'])


    @commands.command(pass_content=True, help="[<prefix>move <posição atual da musica> <nova posição da musica>] exemplo: !move 5 3")
    async def move(self, ctx, *kwargs):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        author_channel = ctx.author.voice

        if (author_channel == None):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")
        author_channel = author_channel.channel

        if (voice == None):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")
        elif (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")

        if (author_channel != voice.channel):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal de audio do Bot.")

        if self.playlist.get(ctx.guild.id) == None:
            return await self.embed_message_send(ctx, "Não tem musicas na lista.")

        if kwargs:
            if (len(kwargs) == 0):
                return await self.embed_message_send(ctx, "Você não mandou argumentos suficientes.")
            elif (len(kwargs) == 1):
                if kwargs[0].isdigit():
                    if int(kwargs[0]) >= 1:
                        music_pos = self.cursor[ctx.guild.id]['locate'] + int(kwargs[0])
                        if music_pos > len(self.playlist[ctx.guild.id])-1:
                            return await self.embed_message_send(ctx, "Não tem essa musica na lista.")
                        
                        self.playlist[ctx.guild.id].insert(
                            self.cursor[ctx.guild.id]['locate']+1, self.playlist[ctx.guild.id].pop(music_pos)
                            )
                        return await self.embed_message_send(ctx, f"Musica movida da {int(kwargs[0])}° posição para a 1° posição.")
                    else:
                        return await self.embed_message_send(ctx, "Não tem essa musica na lista.")
            else:
                if kwargs[0].isdigit() and kwargs[1].isdigit():
                    if (int(kwargs[0]) >= 1) and (int(kwargs[1]) >= 1):
                        start_pos = self.cursor[ctx.guild.id]['locate'] + int(kwargs[0])
                        end_pos = self.cursor[ctx.guild.id]['locate'] + int(kwargs[1])

                        if (start_pos > len(self.playlist[ctx.guild.id])-1) or (end_pos > len(self.playlist[ctx.guild.id])-1):
                            return await self.embed_message_send(ctx, "Não tem essa musica na lista.")

                        self.playlist[ctx.guild.id].insert(
                            self.cursor[ctx.guild.id]['locate'] + end_pos,
                            self.playlist[ctx.guild.id].pop(start_pos)
                            )
                        return await self.embed_message_send(ctx, f"Musica movida da {int(kwargs[0])}° posição para a {int(kwargs[1])}° posição.")
                    else:
                        return await self.embed_message_send(ctx, "Não tem essa musica na lista ou a posição da musica não existe.")


    @commands.command(pass_content=True, help="[<prefix>remove <posição atual da musica>]")
    async def remove(self, ctx, *kwargs):
        voice = get(self.client.voice_clients, guild=ctx.guild)
        author_channel = ctx.author.voice

        if (author_channel == None):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")
        author_channel = author_channel.channel

        if (voice == None):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")
        elif (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")

        if (author_channel != voice.channel):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal de audio do Bot.")

        if self.playlist.get(ctx.guild.id) == None:
            return await self.embed_message_send(ctx, "Não tem musicas na lista.")

        if kwargs:
            if (len(kwargs) == 0):
                return await self.embed_message_send(ctx, "Você não mandou argumentos suficientes.")
            else:
                if kwargs[0].isdigit():
                    remove_pos = int(kwargs[0])
                    if remove_pos <= 0:
                        return await self.embed_message_send(ctx, "Não tem essa musica na lista.")
                    elif (self.cursor[ctx.guild.id]['locate'] + remove_pos > len(self.playlist[ctx.guild.id])-1):
                        return await self.embed_message_send(ctx, "Não tem essa musica na lista.")
                    else:
                        self.playlist[ctx.guild.id].pop(self.cursor[ctx.guild.id]['locate'] + remove_pos)
                        return await self.embed_message_send(ctx, f"{remove_pos}° musica removida da lista.")



async def setup(client):
    await client.add_cog(MusicController(client))