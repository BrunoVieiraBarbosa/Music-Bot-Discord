# music-bot-discord
Um simples bot de musica para o Discord. Um dos primeiros que criei.


### Os recursos desse Bot de música são:
* **Tocar** a música
* **Adicionar** e **remover** músicas
* **Alterar** a ordem das músicas.
* **Repetir** uma ou várias vezes
* **Voltar** para a música anterior
* **Ver informações** da música que está ouvindo
* **Pausar**, **continuar**, **parar** e **pular** a música
* **Alterar** o **volume**
* **Apagar** mensagens

### OBS
Alterar o arquivo "youtube_dl\extractor\youtube.py" na linha 1794

**de**: 'uploader_id': self._search_regex(r'/(?:channel|user)/([^/?&#]+)', owner_profile_url, 'uploader id') if owner_profile_url else None,

**para**: 'uploader_id': self._search_regex(r'/(?:channel/|user/|@)([^/?&#]+)', owner_profile_url, 'uploader id', default=None),**

### Exemplo do Bot em funcionamento:
![Pedido de música](https://github.com/Bruno8666/music-bot-discord/blob/main/exemplo/play.png)
