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


    async def next_music(self, ctx):
        if str(ctx.guild.id) not in self.playlist:
            return

        next_play = None
        if self.play_again[str(ctx.guild.id)] >= 1:
            next_play = self.cursor[str(ctx.guild.id)]['locate']
            if self.play_again[str(ctx.guild.id)] == 1:
                self.play_again[str(ctx.guild.id)] = 0
        else:
            next_play = self.cursor[str(ctx.guild.id)]['locate'] + 1

        self.cursor[str(ctx.guild.id)]['locate'] = next_play

        if next_play > len(self.playlist[str(ctx.guild.id)])-1:
            self.playing[str(ctx.guild.id)] = False
        else:
            await self.play_now(ctx)


    async def get_playlist_links(self, url: str):
        playlist = set(re.findall(re.compile(r"watch\?v=\S+?list="), requests.get(url).text))
        return list(
            map(
                lambda x: "https://www.youtube.com/" + x.replace("\\u0026list=", ""),
                playlist
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
        user = self.playlist[str(ctx.guild.id)][self.cursor[str(ctx.guild.id)]['locate']]['user']
        metadata = self.playlist[str(ctx.guild.id)][self.cursor[str(ctx.guild.id)]['locate']]['metadata'].copy()

        metadata["view_count"] = f'{metadata["view_count"]:,}'.replace(',', '.')

        metadata["duration"] = datetime.strptime(timedelta(seconds=metadata["duration"]).__str__(), '%H:%M:%S').strftime('%H:%M:%S')
        metadata["upload_date"] = datetime.strptime(metadata["upload_date"], '%Y%m%d').strftime('%d-%m-%Y')
        
        if self.time_playing[str(ctx.guild.id)]['time'] != None:
            time_ = int((time.time() - self.time_playing[str(ctx.guild.id)]['time']) + self.time_playing[str(ctx.guild.id)]['total'])
        else:
            time_ = int(self.time_playing[str(ctx.guild.id)]['total'])

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

        self.playing[str(ctx.guild.id)] = True

        self.time_playing[str(ctx.guild.id)]['time'] = time.time()
        self.time_playing[str(ctx.guild.id)]['total'] = 0

        URL = self.playlist[str(ctx.guild.id)][self.cursor[str(ctx.guild.id)]['locate']]['url']

        voice.play(FFmpegPCMAudio(URL, **self.ffmpeg_options), after = lambda _: asyncio.run(self.next_music(ctx)))
        voice.source = discord.PCMVolumeTransformer(voice.source)
        voice.source.volume = 1.0
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


    async def remove_reaction(self, msg):
        try:
            await msg.clear_reactions()
        except discord.errors.NotFound:
            pass


    async def update_player_reaction(self, guild_id, new_msg):
        if (self.emoji[guild_id]['player'] != None):
            await self.remove_reaction(self.emoji[guild_id]['player'])
        [await new_msg.add_reaction(x) for x in ("⏮️", "⏸️", "▶️", "⏭️", "⏹️", "🔁")]
        self.emoji[guild_id]['player'] = new_msg


    async def update_queue_reaction(self, guild_id, new_msg):
        if (self.emoji[guild_id]['queue'] != None):
            await self.remove_reaction(self.emoji[guild_id]['queue'])
        [await new_msg.add_reaction(x) for x in ("⬅️", "➡️")]
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
                        self.actual_page[str(user.guild.id)]['page'] -= 1
                        msg = await self.fila(self.cursor[str(user.guild.id)]['ctx'], self.actual_page[str(user.guild.id)])
                        if (msg != None):
                            await asyncio.sleep(3)
                            await msg.delete()

                elif (reaction.emoji == "➡️"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        self.actual_page[str(user.guild.id)]['page'] += 1
                        msg = await self.fila(self.cursor[str(user.guild.id)]['ctx'], self.actual_page[str(user.guild.id)])
                        if (msg != None):
                            await asyncio.sleep(3)
                            await msg.delete()


                #Player de musica
                if (reaction.emoji == "⏮️"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        msg = await self.back(self.cursor[str(user.guild.id)]['ctx'])
                        await asyncio.sleep(3)
                        await msg.delete()

                elif (reaction.emoji == "⏸️"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        msg = await self.pause(self.cursor[str(user.guild.id)]['ctx'])
                        await asyncio.sleep(3)
                        await msg.delete()

                elif (reaction.emoji == "▶️"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        msg = await self.resume(self.cursor[str(user.guild.id)]['ctx'])
                        await asyncio.sleep(3)
                        await msg.delete()

                elif (reaction.emoji == "⏭️"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        msg = await self.skip(self.cursor[str(user.guild.id)]['ctx'])
                        await asyncio.sleep(3)
                        await msg.delete()
                
                elif (reaction.emoji == "⏹️"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        msg = await self.stop(self.cursor[str(user.guild.id)]['ctx'])
                        await asyncio.sleep(3)
                        await msg.delete()
                
                elif (reaction.emoji == "🔁"):
                    if (reaction.count == 2):
                        await reaction.remove(user=user)
                    if await on_same_channel(self, user.guild, user.voice):
                        msg = await self.repeat(self.cursor[str(user.guild.id)]['ctx'])
                        await asyncio.sleep(3)
                        await msg.delete()


    #Comandos do Usuario
    @commands.command(pass_content=True, help="[<prefix>play <Nome ou link da musica>] - Toca um musica ou a adiciona na lista.")
    async def play(self, ctx, *kwargs):
        if len(kwargs) < 1:
            return await ctx.send("```Você não mandou a musica.```")

        voice = get(self.client.voice_clients, guild=ctx.guild)

        #Verifica se o usuario não está em um canal de audio
        if not await self.user_on_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")

        #Verifica se o bot não está em um canal de audio
        if not await self.bot_on_channel(ctx):
            await ctx.author.voice.channel.connect()

        #Verifica se não estão no mesmo canal e se o bot está tocando alguma musica ou está em pause.
        if not await self.bot_same_channel(ctx) and (voice.is_playing() or voice.is_paused()):
            return await self.embed_message_send(ctx, "Ja estou tocando uma musica em outro canal de audio.")

        #Verifica se não estão no mesmo canal e se o bot não está tocando alguma musica ou em pause.
        if not await self.bot_same_channel(ctx) and (not voice.is_playing() and not voice.is_paused()):
            await voice.move_to(ctx.author.voice.channel)

        if str(ctx.guild.id) not in self.playlist:
            self.playlist[str(ctx.guild.id)] = []

        if str(ctx.guild.id) not in self.playing:
            self.playing[str(ctx.guild.id)] = False

        if str(ctx.guild.id) not in self.cursor:
            self.cursor[str(ctx.guild.id)] = {'locate': -1, 'ctx': ctx}

        if str(ctx.guild.id) not in self.time_playing:
            self.time_playing[str(ctx.guild.id)] = {'time': None, 'total': 0}

        if str(ctx.guild.id) not in self.play_again:
            self.play_again[str(ctx.guild.id)] = 0

        if str(ctx.guild.id) not in self.emoji:
            self.emoji[str(ctx.guild.id)] = {'player': None, 'queue': None}

        qtde, individual = 0, False
        if kwargs[-1].isdigit() and ('https://www.youtube.com/' in kwargs[0] or 'https://youtu.be/' in kwargs[0]):
            url = ' '.join(kwargs[:-1])
            qtde = int(kwargs[-1])
        elif ('https://www.youtube.com/' in kwargs[0] or 'https://youtu.be/' in kwargs[0]):
            url = kwargs[0]
        else:
            url = ' '.join(kwargs)

        if (url.startswith('https://www.youtube.com/') or url.startswith('https://youtu.be/')) and ('&list=' in url and qtde > 1):
            #Playlist
            url = f'https://www.youtube.com/playlist?list={url[url.index("&list=")+6:]}'
            links = await self.get_playlist_links(url)
            links = links[:qtde]
            msg = await ctx.send(f"```Carregando {len(links)} musica{'s' if len(links) > 1 else ''}.```")
            for link in links:
                data = await self.get_url(link)
                if data:
                    plural = 's' if links.index(link)+1 > 1 else ''
                    await msg.edit(content=f"```{links.index(link)+1} musica{plural} adicionada{plural} ```")
                    self.playlist[str(ctx.guild.id)].append({'url': data[1], 'metadata': data[0].copy(), 'user': ctx.author})

        else:
            individual = True

        if individual:
            data = await self.get_url(url)
            if not data:
                return await self.embed_message_send(ctx, "Musica não encontrada.")

            self.playlist[str(ctx.guild.id)].append({'url': data[1], 'metadata': data[0].copy(), 'user': ctx.author})
            pos = (len(self.playlist[str(ctx.guild.id)])-1) - self.cursor[str(ctx.guild.id)]['locate']

            if (pos > 0 and self.cursor[str(ctx.guild.id)]['locate'] > -1):
                await self.embed_message_update_queue(ctx, data[0].copy(), pos)

        if self.cursor[str(ctx.guild.id)]['locate'] == -1 and len(self.playlist[str(ctx.guild.id)]) > 0:
            self.cursor[str(ctx.guild.id)]['locate'] = 0
            await self.play_now(ctx)
            await self.now(ctx)
        elif self.playing[str(ctx.guild.id)] == False and (self.cursor[str(ctx.guild.id)]['locate'] == len(self.playlist[str(ctx.guild.id)])-1):
            await self.play_now(ctx)
            await self.now(ctx)



    @commands.command(pass_content=True, help="Reproduz a musica novamente quando acabar.")
    async def repeat(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if not await self.bot_on_channel(ctx):
            return await self.embed_message_send(ctx, "Não estou em um canal de audio.")

        if not await self.user_on_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")

        if not await self.bot_same_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal que eu.") 

        if (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "Não estou tocando nenhuma musica.")


        if (self.play_again[str(ctx.guild.id)] == 0):
            self.play_again[str(ctx.guild.id)] = 1
            return await self.embed_message_send(ctx, "O bot ira repitir uma unica vez essa musica.")

        elif (self.play_again[str(ctx.guild.id)] == 1):
            self.play_again[str(ctx.guild.id)] = 2
            return await self.embed_message_send(ctx, "O bot ficará repitindo essa musica.")

        else:
            self.play_again[str(ctx.guild.id)] = 0
            return await self.embed_message_send(ctx, "O bot não ira repitir essa musica.")


    @commands.command(pass_content=True, help="Reproduz a musica anterior")
    async def back(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if not await self.bot_on_channel(ctx):
            return await self.embed_message_send(ctx, "Não estou em um canal de audio.")

        if not await self.user_on_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")

        if not await self.bot_same_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal que eu.")


        if self.cursor[str(ctx.guild.id)]['locate'] > -1 and self.playing[str(ctx.guild.id)] == False:
            self.cursor[str(ctx.guild.id)]['locate'] -= 1
            return await self.play_now(ctx)


        if (self.cursor[str(ctx.guild.id)]['locate'] - 2 >= -1) and (self.play_again[str(ctx.guild.id)] == 0):
            self.cursor[str(ctx.guild.id)]['locate'] -= 2
            voice.stop()
            await self.embed_message_send(ctx, "Reproduzindo musica anterior.")
            await asyncio.sleep(1.5)
            if (voice.is_playing() or voice.is_paused()):
                return await self.now(ctx)

        elif (self.cursor[str(ctx.guild.id)]['locate'] - 1 >= 0) and (self.play_again[str(ctx.guild.id)] >= 1):
            self.cursor[str(ctx.guild.id)]['locate'] -= 1
            voice.stop()
            return await self.embed_message_send(ctx, "Reproduzindo musica anterior.")
        else:
            return await self.embed_message_send(ctx, "Não tem musicas anteriores.")



    @commands.command(pass_context=True, help="Exibe informações da musica que esta sendo tocada.")
    async def now(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if not await self.bot_on_channel(ctx):
            return await self.embed_message_send(ctx, "Não tem musica tocando.")

        if (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "Não estou tocando nenhuma musica.")
        if str(ctx.guild.id) not in self.playing:
            return await self.embed_message_send(ctx, "Não tem musica tocando.")
        elif not self.playing[str(ctx.guild.id)]:
            return await self.embed_message_send(ctx, "Não tem musica tocando.")
        else:
            msg = await self.embed_message_update_music(ctx)
            await self.update_player_reaction(str(ctx.guild.id), msg)


    @commands.command(pass_content=True, help="Pausa a musica atual.")
    async def pause(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if not await self.user_on_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")

        if not await self.bot_on_channel(ctx):
            return await self.embed_message_send(ctx, "Não estou em um canal de audio.")

        if (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "O bot não esta tocando nenhuma musica.")
        elif voice.is_paused():
            return await self.embed_message_send(ctx, "A musica ja está pausada.")

        if not await self.bot_same_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal que eu.")

        self.time_playing[str(ctx.guild.id)]['total'] += (time.time() - self.time_playing[str(ctx.guild.id)]['time'])
        self.time_playing[str(ctx.guild.id)]['time'] = None

        voice.pause()
        return await ctx.send(embed=discord.Embed(title="\n", color=self.COR, description="Musica pausada com sucesso!"))


    @commands.command(pass_context=True, help="Volta a tocar a musica.")
    async def resume(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if not await self.user_on_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")

        if not await self.bot_on_channel(ctx):
            return await self.embed_message_send(ctx, "Não estou em um canal de audio.")

        if (str(ctx.guild.id) not in self.playing) or (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "Não estou tocando nenhuma musica.")
        elif voice.is_playing():
            return await self.embed_message_send(ctx, "A musica não está pausada.")

        if not await self.bot_same_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal que eu.")

        self.time_playing[str(ctx.guild.id)]['time'] = time.time()
        voice.resume()

        return await ctx.send(embed=discord.Embed(title="\n", color=self.COR, description="Voltando a tocar a musica!"))


    @commands.command(pass_context=True, help="Para de tocar e exclui todas as musicas da fila atual.")
    async def stop(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if not await self.user_on_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")

        if not await self.bot_on_channel(ctx):
            return await self.embed_message_send(ctx, "Não estou em um canal de audio.")

        if (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "Não estou tocando nenhuma musica.")

        if not await self.bot_same_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal que eu.")


        self.playlist[str(ctx.guild.id)] = []
        self.cursor[str(ctx.guild.id)]['locate'] = -1
        self.play_again[str(ctx.guild.id)] = 0

        voice.stop()
        mscpause = discord.Embed( title="\n", color=self.COR, description="Musica parada e todas as musicas da fila atual foram excuidas!")
        return await ctx.send(embed=mscpause)


    @commands.command(pass_context=True, help="Pula para a proxima musica da fila.")
    async def skip(self, ctx):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if not await self.user_on_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")

        if not await self.bot_on_channel(ctx):
            return await self.embed_message_send(ctx, "Não estou em um canal de audio.")
        
        if (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "Não estou tocando nenhuma musica.")

        if not await self.bot_same_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal que eu.")


        if str(ctx.guild.id) not in self.playlist:
            return await self.embed_message_send(ctx, "Não tem musicas na lista.")

        if (len(self.playlist[str(ctx.guild.id)]) == 0):
            return await self.embed_message_send(ctx, "Não tem mais musicas na lista.")

        if self.cursor[str(ctx.guild.id)]['locate'] == len(self.playlist[str(ctx.guild.id)])-1:
            if self.play_again[str(ctx.guild.id)] >= 1:
                self.play_again[str(ctx.guild.id)] = 0
            description = "Não tem musicas na lista."

        elif self.cursor[str(ctx.guild.id)]['locate'] < len(self.playlist[str(ctx.guild.id)])-1:
            if self.play_again[str(ctx.guild.id)] >= 1:
                self.play_again[str(ctx.guild.id)] = 0
            description = "Reproduzindo a proxima musica!"

        voice.stop()
        await ctx.send(embed=discord.Embed(title="\n", color=self.COR, description=description))
        await asyncio.sleep(1.5)
        if (voice.is_playing() or voice.is_paused()):
            return await self.now(ctx)
            


    @commands.command(pass_context=True, help="Aumenta e diminui o volume do audio.")
    async def vol(self, ctx, volume: str = None):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if not await self.user_on_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")

        if not await self.bot_on_channel(ctx):
            return await self.embed_message_send(ctx, "Não estou em um canal de audio.")

        if (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "Não estou tocando nenhuma musica.")

        if not await self.bot_same_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal que eu.")    

        if (volume == ""):
            return await self.embed_message_send(ctx, f"Volume atual: {int(voice.source.volume*100)}")

        if (not volume.isdigit()):
            return await self.embed_message_send(ctx, "Certifique de inserir apenas numeros inteiros apos o comando.")
        
        volume = float(volume) / 100
        
        if (volume <= 1000.0):
            if (voice.source.volume == volume):
                text = f"O volume continua {int(volume*100)}%"
            else:
                text = f"{'Aumentando' if voice.source.volume < volume else 'Diminuindo'} o volume para {int(volume*100)}%"
            voice.source.volume = volume
            return await ctx.send(embed=discord.Embed(title="Volume", color=self.COR, description=text))
        else:
            return await self.embed_message_send(ctx, f"Volume maximo aceito: {int(1000*100)}")


    @commands.command(pass_context=True, help="Lista cada musica da fila.")
    async def fila(self, ctx, page=None):
        if str(ctx.guild.id) not in self.playlist:
            return await self.embed_message_send(ctx, "Não tem musicas na fila.")
        
        if (len(self.playlist[str(ctx.guild.id)]) == 0):
            return await self.embed_message_send(ctx, "Não tem musicas na fila.")

        if str(ctx.guild.id) not in self.actual_page:
            self.actual_page[str(ctx.guild.id)] = {'msg': None, 'page': 0}

        act_page = 1
        msg_reuse = False
    
        if page != self.actual_page[str(ctx.guild.id)]:
            if str(page).isdigit():
                act_page = int(page)
        else:
            msg_reuse = True
            act_page = self.actual_page[str(ctx.guild.id)]['page']
        
        act_page = 1 if act_page <= 0 else act_page
        
        self.actual_page[str(ctx.guild.id)]['page'] = act_page
        
        start = self.cursor[str(ctx.guild.id)]['locate'] + 1 + ((act_page-1) * 10)
        pos = self.cursor[str(ctx.guild.id)]['locate']
        end = start + 10

        if (start > len(self.playlist[str(ctx.guild.id)])-1):
            self.actual_page[str(ctx.guild.id)]['page'] -= 1
            return await self.embed_message_send(ctx, f'Não tem musicas para listar na {act_page}° pagina.')
        
        metadata = self.playlist[str(ctx.guild.id)][self.cursor[str(ctx.guild.id)]['locate']]['metadata']
        author = self.playlist[str(ctx.guild.id)][self.cursor[str(ctx.guild.id)]['locate']]['user']
        text = f"`Tocando Agora`:\n[{metadata['title']}]({metadata['webpage_url']}) - `Pedido por: {author.name}`\n\nAbaixo as musicas da lista"

        mscemb = discord.Embed(title=f"Fila - {act_page}° pagina", description=text, color=self.COR)

        for i, music in enumerate(self.playlist[str(ctx.guild.id)][start:], start):
            metadata = music['metadata']
            author = music['user']
            mscemb.add_field(name=f"{i-pos}° - {metadata['title']}", value=f'Adicionado por {author.name}\n', inline=False)

            if (i+1 == end):
                break

        if msg_reuse:
            await self.actual_page[str(ctx.guild.id)]['msg'].edit(embed=mscemb)
        else:
            self.actual_page[str(ctx.guild.id)]['msg'] = await ctx.send(embed=mscemb)

        return await self.update_queue_reaction(str(ctx.guild.id), self.actual_page[str(ctx.guild.id)]['msg'])


    @commands.command(pass_content=True, help="[<prefix>move <posição atual da musica> <nova posição da musica>] exemplo: !move 5 3")
    async def move(self, ctx, de, para=None):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if not await self.user_on_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")

        if not await self.bot_on_channel(ctx):
            return await self.embed_message_send(ctx, "Não estou em um canal de audio.")

        if (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "Não estou tocando nenhuma musica.")

        if not await self.bot_same_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal que eu.")


        if str(ctx.guild.id) not in self.playlist:
            return await self.embed_message_send(ctx, "Não tem musicas na lista.")

        if str(de).isdigit() and para == None:
            if int(de) >= 1:
                music_pos = self.cursor[str(ctx.guild.id)]['locate'] + int(de)
                if music_pos > len(self.playlist[str(ctx.guild.id)])-1:
                    return await self.embed_message_send(ctx, "Não tem essa musica na lista.")
                
                self.playlist[str(ctx.guild.id)].insert(
                    self.cursor[str(ctx.guild.id)]['locate']+1, self.playlist[str(ctx.guild.id)].pop(music_pos)
                    )
                return await self.embed_message_send(ctx, f"Musica movida da {int(de)}° posição para a 1° posição.")

        elif str(de).isdigit() and str(para).isdigit():
            if (int(str(de)) >= 1) and (int(str(para)) >= 1):
                start_pos = self.cursor[str(ctx.guild.id)]['locate'] + int(str(de))
                end_pos = self.cursor[str(ctx.guild.id)]['locate'] + int(str(para))

                if (start_pos > len(self.playlist[str(ctx.guild.id)])-1) or (end_pos > len(self.playlist[str(ctx.guild.id)])-1):
                    return await self.embed_message_send(ctx, "Não tem essa musica na lista.")

                self.playlist[str(ctx.guild.id)].insert(
                    self.cursor[str(ctx.guild.id)]['locate'] + end_pos,
                    self.playlist[str(ctx.guild.id)].pop(start_pos)
                    )
                return await self.embed_message_send(ctx, f"Musica movida da {int(str(de))}° posição para a {int(str(para))}° posição.")

        return await self.embed_message_send(ctx, "Não tem essa musica na lista ou a posição da musica não existe.")


    @commands.command(pass_content=True, help="[<prefix>remove <posição atual da musica>]")
    async def remove(self, ctx, index):
        voice = get(self.client.voice_clients, guild=ctx.guild)

        if not await self.user_on_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar em um canal de audio.")

        if not await self.bot_on_channel(ctx):
            return await self.embed_message_send(ctx, "Não estou em um canal de audio.")

        if (not voice.is_playing() and not voice.is_paused()):
            return await self.embed_message_send(ctx, "Não estou tocando nenhuma musica.")

        if not await self.bot_same_channel(ctx):
            return await self.embed_message_send(ctx, "Você precisa estar no mesmo canal que eu.")


        if str(ctx.guild.id) not in self.playlist:
            return await self.embed_message_send(ctx, "Não tem musicas na lista.")

        if str(index).isdigit():
            remove_pos = int(str(index))
            if remove_pos <= 0:
                return await self.embed_message_send(ctx, "Não tem essa musica na lista.")
            elif (self.cursor[str(ctx.guild.id)]['locate'] + remove_pos > len(self.playlist[str(ctx.guild.id)])-1):
                return await self.embed_message_send(ctx, "Não tem essa musica na lista.")
            else:
                self.playlist[str(ctx.guild.id)].pop(self.cursor[str(ctx.guild.id)]['locate'] + remove_pos)
                return await self.embed_message_send(ctx, f"{remove_pos}° musica removida da lista.")



async def setup(client):
    await client.add_cog(MusicController(client))