import disnake
from disnake.ext import commands
import yt_dlp as youtube_dl
import os
import requests
import random
import xml.etree.ElementTree as ET
import aiohttp
import asyncio
from PIL import Image
import moviepy.editor as mp

bot = commands.Bot(command_prefix="!", intents=disnake.Intents.all(), help_command=None)
token = "ТОКЕН БОТА"

layout_map = {
    '`': 'ё', 'q': 'й', 'w': 'ц', 'e': 'у', 'r': 'к', 't': 'е', 'y': 'н', 'u': 'г', 'i': 'ш', 'o': 'щ', 'p': 'з',
    'a': 'ф', 's': 'ы', 'd': 'в', 'f': 'а', 'g': 'п', 'h': 'р', 'j': 'о', 'k': 'л', 'l': 'д',
    'z': 'я', 'x': 'ч', 'c': 'с', 'v': 'м', 'b': 'и', 'n': 'т', 'm': 'ь',
    ',': 'б', '.': 'ю', '/': '.', '[': 'х', ']': 'ъ', ';': 'ж', "'": 'э',
    'Q': 'Й', 'W': 'Ц', 'E': 'У', 'R': 'К', 'T': 'Е', 'Y': 'Н', 'U': 'Г', 'I': 'Ш', 'O': 'Щ', 'P': 'З',
    'A': 'Ф', 'S': 'Ы', 'D': 'В', 'F': 'А', 'G': 'П', 'H': 'Р', 'J': 'О', 'K': 'Л', 'L': 'Д',
    'Z': 'Я', 'X': 'Ч', 'C': 'С', 'V': 'М', 'B': 'И', 'N': 'Т', 'M': 'Ь',
}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} ({bot.user.id})")
    print("Bot is ready!")

def log_command(inter):
    user = inter.author
    print(f"[Команда: {inter.application_command.name}] Пользователь: {user} (ID: {user.id}) в канале: {inter.channel}")

# Музыка и Войс клиент
music_queue = []
voice_client = None

class MusicPlayer(disnake.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @disnake.ui.button(label="Join", style=disnake.ButtonStyle.green)
    async def join(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        global voice_client
        voice_channel = inter.author.voice.channel

        if voice_client and voice_client.is_connected():
            await inter.response.send_message("Бот уже подключен к голосовому каналу!", ephemeral=True)
        else:
            voice_client = await voice_channel.connect()
            await inter.response.send_message(f"Бот присоединился к каналу: **{voice_channel.name}**", ephemeral=True)

    @disnake.ui.button(label="Play", style=disnake.ButtonStyle.green)
    async def play(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        global voice_client
        if not voice_client or not voice_client.is_connected():
            await inter.response.send_message("Бот не подключен к голосовому каналу!", ephemeral=True)
            return

        if not music_queue:
            await inter.response.send_message("Очередь пуста!", ephemeral=True)
            return
        
        song = music_queue.pop(0)
        source = await disnake.FFmpegOpusAudio.from_probe(song['url'], executable="ffmpeg")
        voice_client.play(source)

        await inter.response.send_message(f"Воспроизводится: **{song['title']}**", ephemeral=True)

    @disnake.ui.button(label="Pause", style=disnake.ButtonStyle.blurple)
    async def pause(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        global voice_client
        if voice_client and voice_client.is_playing():
            voice_client.pause()
            await inter.response.send_message("Музыка приостановлена.", ephemeral=True)
        else:
            await inter.response.send_message("Музыка не воспроизводится.", ephemeral=True)

    @disnake.ui.button(label="Resume", style=disnake.ButtonStyle.green)
    async def resume(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        global voice_client
        if voice_client and voice_client.is_paused():
            voice_client.resume()
            await inter.response.send_message("Музыка возобновлена.", ephemeral=True)
        else:
            await inter.response.send_message("Музыка не приостановлена.", ephemeral=True)

    @disnake.ui.button(label="Skip", style=disnake.ButtonStyle.red)
    async def skip(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        global voice_client
        if voice_client:
            if music_queue:
                voice_client.stop()  # Stop current song
                await self.play(button, inter)  # Play next song
                await inter.response.send_message("Пропуск песни.", ephemeral=True)
            else:
                await inter.response.send_message("Очередь пуста!", ephemeral=True)
        else:
            await inter.response.send_message("Бот не подключен к голосовому каналу!", ephemeral=True)

    @disnake.ui.button(label="Stop", style=disnake.ButtonStyle.red)
    async def stop(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
        global voice_client
        if voice_client:
            await voice_client.disconnect()
            await inter.response.send_message("Музыка остановлена и бот отключен от голосового канала.", ephemeral=True)
        else:
            await inter.response.send_message("Бот не подключен к голосовому каналу!", ephemeral=True)

# Команда помощи
@bot.slash_command(name="help", description="Отобразить список команд", dm_permission=True)
async def custom_help(inter):
    log_command(inter)
    embed = disnake.Embed(title="Список команд", color=disnake.Color.blue())
    embed.add_field(name="/music [ссылка]", value="Воспроизведение музыки с указанной ссылки.", inline=False)
    embed.add_field(name="/site", value="Ссылка на сайт Multool от WessiX.", inline=False)
    embed.add_field(name="/dtiktok [ссылка]", value="Скачивание видео с TikTok. (Лимит 50 МБ)", inline=False)
    embed.add_field(name="/dyoutube [ссылка]", value="Скачивание видео с YouTube. (Лимит 50 МБ)", inline=False)
    embed.add_field(name="/translate [текст]", value="Перевод текста с неправильной раскладки клавиатуры.", inline=False)
    embed.add_field(name="/gif", value="Создает GIF из прикрепленного изображения или видео.", inline=False)
    embed.add_field(name="/updatelog", value="Показывает информацию об обновлении", inline=False)
    embed.add_field(name="/rule34", value="Находит фото по указанному тегу", inline=False)
    await inter.response.send_message(embed=embed)

# Перевод раскладки клавиатуры
@bot.slash_command(name="translate", description="Перевод текста с неправильной раскладки клавиатуры", dm_permission=True)
async def translate(inter, text: str):
    translated_text = ''.join([layout_map.get(char, char) for char in text])
    await inter.response.send_message(translated_text)

@bot.slash_command(name="music", description="Воспроизведение музыки с указанной ссылки.", dm_permission=False)
async def music(inter, url: str):
    log_command(inter)

    voice_channel = inter.author.voice.channel
    if not voice_channel:
        await inter.response.send_message("Вы не подключены к голосовому каналу!")
        return

    await inter.response.defer()

    global voice_client
    if not voice_client:
        voice_client = await voice_channel.connect()

    ydl_opts = {
        'format': 'bestaudio/best',
        'noplaylist': True,
        'extractaudio': True,
        'verbose': True,
    }

    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            song_info = {
                'title': info['title'],
                'url': info['url'],
            }
            music_queue.append(song_info)  # Добавление музыки в очередь

        if len(music_queue) == 1:  # Если первая песня в очереди
            await inter.followup.send("Музыка добавлена в очередь.", view=MusicPlayer())  # Старт с помощью кнопки

        await inter.followup.send(f"Добавлено в очередь: **{song_info['title']}**")
    except Exception as e:
        await inter.followup.send(content=f"Не удалось воспроизвести музыку: {str(e)}")
        return

# Команда обновлений
@bot.slash_command(name="updatelog", description="Показать информацию об обновлении", dm_permission=True)
async def updatelog(inter):
    log_command(inter)
    embed = disnake.Embed(title="Обновление бота", color=disnake.Color.green())
    embed.add_field(name="Изменения:", value="Добавлены команды для работы с музыкой, добавлены новые кнопки управления.", inline=False)
    await inter.response.send_message(embed=embed)

# Команда для получения ссылки на сайт
@bot.slash_command(name="site", description="Ссылка на сайт Multool от WessiX", dm_permission=True)
async def site(inter):
    log_command(inter)
    embed = disnake.Embed(title="Ссылка", description="[Нажми на меня](https://weissx.net/index.php)", color=disnake.Color.blue())
    await inter.response.send_message(embed=embed)

# Команда для получения изображения с rule34.xxx
@bot.slash_command(name="rule34", description="Искать изображения на rule34", dm_permission=True)
async def rule34(inter, query: str):
    log_command(inter)
    await inter.response.defer()

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }

    url = f"https://rule34.xxx/index.php?page=dapi&s=post&q=index&tags={query}&limit=100"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        root = ET.fromstring(response.content)
        posts = root.findall("post")

        if posts:
            random_post = random.choice(posts)
            image_url = random_post.attrib.get("file_url")
            await inter.followup.send(image_url)
        else:
            await inter.followup.send("Изображения не найдены по данному запросу.")
    else:
        await inter.followup.send(f"Ошибка при запросе к API: {response.status_code}")

# Загрузка видео с TikTok
@bot.slash_command(name="dtiktok", description="Скачать видео с TikTok", dm_permission=True)
async def dtiktok(inter, url: str):
    await download_and_send_video(inter, url, "TikTok")

# Загрузка видео с YouTube
@bot.slash_command(name="dyoutube", description="Скачать видео с YouTube", dm_permission=True)
async def dyoutube(inter, url: str):
    await download_and_send_video(inter, url, "YouTube")

# Создание GIF из изображения или видео
@bot.slash_command(name="gif", description="Создать GIF из прикрепленного изображения или видео", dm_permission=True)
async def gif(inter):
    log_command(inter)
    
    await inter.response.send_message("Отправьте видео или изображение в этот чат.")
    
    def check(msg):
        return msg.author == inter.author and msg.channel == inter.channel and msg.attachments
    
    try:
        # Ожидание сообщения от пользователя с вложением (изображение/видео)
        message = await bot.wait_for("message", timeout=60.0, check=check)
        attachment = message.attachments[0]
        file_path = f"downloads/{attachment.filename}"

        if not os.path.exists('downloads'):
            os.makedirs('downloads')

        await attachment.save(file_path)

        # Проверка типа вложения (изображение или видео)
        if file_path.endswith(('.png', '.jpg', '.jpeg')):
            gif_path = file_path.rsplit('.', 1)[0] + ".gif"
            try:
                image = Image.open(file_path)
                image.save(gif_path, format='GIF', save_all=True, duration=200, loop=0)
                await message.channel.send(file=disnake.File(gif_path))
            except Exception as e:
                await message.channel.send(f"Ошибка при создании GIF: {str(e)}")
            finally:
                os.remove(file_path)
                if os.path.exists(gif_path):
                    os.remove(gif_path)

        elif file_path.endswith(('.mp4', '.mov', '.avi', '.mkv')):
            gif_path = file_path.rsplit('.', 1)[0] + ".gif"
            try:
                clip = mp.VideoFileClip(file_path)
                clip = clip.subclip(0, min(clip.duration, 10))  # Обрезаем до 10 секунд
                clip.write_gif(gif_path)
                await message.channel.send(file=disnake.File(gif_path))
            except Exception as e:
                await message.channel.send(f"Ошибка при создании GIF: {str(e)}")
            finally:
                os.remove(file_path)
                if os.path.exists(gif_path):
                    os.remove(gif_path)
        else:
            await message.channel.send("Неподдерживаемый формат файла. Пожалуйста, прикрепите изображение или видео.")
    
    except asyncio.TimeoutError:
        await inter.followup.send("Время ожидания истекло. Пожалуйста, отправьте файл в течение 60 секунд после команды.")


    log_command(inter)

    if not inter.message.attachments:
        await inter.response.send_message("Пожалуйста, прикрепите изображение или видео для преобразования в GIF.")
        return

    attachment = inter.message.attachments[0]
    file_path = f"downloads/{attachment.filename}"

    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    await attachment.save(file_path)

    if file_path.endswith(('.png', '.jpg', '.jpeg')):
        gif_path = file_path.rsplit('.', 1)[0] + ".gif"
        try:
            image = Image.open(file_path)
            image.save(gif_path, format='GIF', save_all=True, duration=200, loop=0)
            await inter.followup.send(file=disnake.File(gif_path))
        except Exception as e:
            await inter.response.send_message(f"Ошибка при создании GIF: {str(e)}")
        finally:
            os.remove(file_path)
            if os.path.exists(gif_path):
                os.remove(gif_path)

    elif file_path.endswith(('.mp4', '.mov', '.avi', '.mkv')):
        gif_path = file_path.rsplit('.', 1)[0] + ".gif"
        try:
            clip = mp.VideoFileClip(file_path)
            clip = clip.subclip(0, min(clip.duration, 10))  # Обрезаем до 10 секунд
            clip.write_gif(gif_path)
            await inter.followup.send(file=disnake.File(gif_path))
        except Exception as e:
            await inter.response.send_message(f"Ошибка при создании GIF: {str(e)}")
        finally:
            os.remove(file_path)
            if os.path.exists(gif_path):
                os.remove(gif_path)
    else:
        await inter.response.send_message("Неподдерживаемый формат файла. Пожалуйста, прикрепите изображение или видео.")

@bot.event
async def on_slash_command_error(inter, error):
    if isinstance(error, commands.CommandNotFound):
        await inter.response.send_message("Неверная команда. Используйте `/help` для просмотра доступных команд.")
    else:
        print(f"Произошла ошибка: {error}")

bot.run(f"token")
