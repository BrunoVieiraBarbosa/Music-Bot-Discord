from youtube_dl import YoutubeDL
import requests, re


YDL_OPTION = {'format': 'bestaudio/best', 'noplaylist':'True', 'quiet':'True'}


async def get_playlist_links(url: str):
    playlist = set(re.findall(re.compile(r"watch\?v=\S+?list="), requests.get(url).text))
    return list(
        map(
            lambda x: "https://www.youtube.com/" + x.replace("\\u0026list=", ""),
            playlist
        )
    )


async def get_url(url: str):
    try:
        with YoutubeDL(YDL_OPTION) as ydl:
            if url.startswith("https://") or url.startswith("http://"):
                info = ydl.extract_info(url, download=False)
            else:
                info = ydl.extract_info(f'ytsearch:{url}', download=False)['entries'][0]
        URL = info['formats'][0]['url']
        return info, URL
    except Exception:
        return False