import hashlib
import os
import re
import secrets
import time
from typing import Union

import httpx
from aiogram import Bot
from aiogram.types import (
    CallbackQuery,
    Message,
    VideoNote,
    Video,
    InlineQuery,
    FSInputFile,
    URLInputFile,
    InlineQueryResultArticle,
    InputTextMessageContent,
    InputMediaAudio,
)
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.keyboards.inline import Inlines
from app.models import Music, User
from app.services.song_process import Song, YtDownload
from app.utils.bot_data import BotData
from app.config import config


class MusicHelper:

    @staticmethod
    def photo_resize(url: str, size: int = 300) -> str:
        """
        Resize YouTube Music thumbnail URL when possible.
        Falls back to the original URL if the expected format
        is not present.
        """
        if not url:
            return url

        if "=" not in url:
            return url

        url_parts = url.split("=")

        if len(url_parts) < 2:
            return url

        url_parts[1] = f"w{size}-h{size}"

        return "=".join(url_parts)

    @staticmethod
    async def get_cover(url: str):
        if not url:
            return None

        try:
            resized_url = MusicHelper.photo_resize(url, 100)

            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(resized_url)
                response.raise_for_status()

                return response.content

        except Exception as e:
            print(f"Error getting cover: {e}")
            return None

    @staticmethod
    async def get_musics_info(platforms, sign, song_id):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            )
        }

        url = f"https://song.link/{sign}/{song_id}"

        async with httpx.AsyncClient(
            headers=headers,
            timeout=10
        ) as client:

            response = await client.get(url)
            response.raise_for_status()

            text = response.text

        extracted_links = {}

        for key, pattern in platforms.items():
            match = re.search(pattern, text)

            if not match:
                extracted_links[key] = None
                continue

            if key in ["title", "artist"]:
                extracted_links[key] = match.group(1)
            else:
                extracted_links[key] = match.group(0)

        return extracted_links

    @staticmethod
    async def music_links(name: str, song_id: str) -> dict:

        default = {
            "youtube": f"https://www.youtube.com/watch?v={song_id}",
            "apple_music": (
                "https://music.apple.com/us/search?"
                f"term={name}"
            ),
            "spotify": (
                "https://open.spotify.com/search/"
                f"{name}"
            ),
            "soundcloud": (
                "https://soundcloud.com/search?q="
                f"{name}"
            ),
        }

        platforms = {
            "youtube": r'https://www\.youtube\.com/watch\?v=[\w-]+',
            "apple_music": r'https://geo\.music\.apple\.com[^\s"]+',
            "spotify": r'https://open\.spotify\.com/track/[^\s"]+',
            "soundcloud": r'https://soundcloud\.com/[^\s"]+',
            "deezer": r'https://www\.deezer\.com/track/[^\s"]+',
            "audiomack": r'https://audiomack\.com/song/[^\s"]+',
        }

        try:
            extracted_links = await MusicHelper.get_musics_info(
                platforms,
                "y",
                song_id
            )

            return {
                "api": True,
                **extracted_links
            }

        except Exception as e:
            print(f"Error getting music links: {e}")

            return default

    @staticmethod
    async def get_song(song_id, db) -> Music:
        """
        Get a song by its database ID.
        """
        result = await db.execute(
            select(Music).filter(Music.id == song_id)
        )

        return result.scalar_one_or_none()


class HandlersHelper:

    def __init__(
        self,
        data: Union[CallbackQuery, Message],
        bot_data: BotData,
        bot: Bot,
        db: AsyncSession = None,
        user: User = None
    ):
        self.bot_data = bot_data
        self.texts = bot_data.texts
        self.data = data
        self.bot = bot
        self.db = db
        self.user = user

    @staticmethod
    def fullname_filter(text: str, song: Music):

        artists = ", ".join(
            artist["name"]
            for artist in song.artists
        )

        filters = {
            "<song_title>": song.title,
            "<song_artists>": artists,
        }

        for filter_, value in filters.items():
            text = text.replace(filter_, value)

        return text

    async def send_music_data(
        self,
        song_id: str,
        deleted=False
    ):
        texts = self.texts
        inlines = Inlines(texts)

        if isinstance(self.data, CallbackQuery):
            chat_id = self.data.message.chat.id

            if deleted:
                msg_id = None
            else:
                msg_id = self.data.message.message_id

        else:
            chat_id = self.data.chat.id
            msg_id = self.data.message_id

        msg = await self.bot.send_message(
            chat_id,
            self.texts.load_icon,
            reply_to_message_id=msg_id
        )

        result = await self.db.execute(
            select(Music).filter(Music.id == song_id)
        )

        song = result.scalar_one_or_none()

        if not song:
            await msg.delete()

            return await self.bot.send_message(
                chat_id,
                texts.not_found,
                reply_to_message_id=msg_id
            )

        photo = song.photo

        full_name = self.fullname_filter(
            self.texts.song_fullname,
            song
        )

        caption = self.fullname_filter(
            self.texts.song_caption,
            song
        )

        if song.details:
            details = song.details

        else:
            details = await MusicHelper.music_links(
                full_name,
                song_id
            )

            song.details = details

            await self.db.commit()

        keyboard = inlines.music_data(
            song_id,
            full_name,
            details
        )

        try:
            await self.bot.send_photo(
                chat_id,
                photo,
                caption=caption,
                reply_markup=keyboard
            )

            await msg.delete()

        except Exception as e:
            print(f"Error sending music data: {e}")

            await msg.edit_text(
                texts.not_found
            )

    @staticmethod
    async def music_download(song):

        album_name = ""

        if song.album:
            album_name = song.album.get("name", "")

        music_data = {
            "title": song.title,
            "artist": [
                artist["name"]
                for artist in song.artists
            ],
            "album": album_name,
            "photo": MusicHelper.photo_resize(
                song.photo,
                200
            ),
        }

        yt = YtDownload(music_data)

        await yt.download_audio_from_id(song.id)

        if not os.path.exists(yt.path):
            raise FileNotFoundError(
                "Audio download failed."
            )

        return yt.path

    @staticmethod
    async def add_result_in_db(
        results,
        db
    ):

        values = []

        for result in results:

            if "videoId" not in result:
                continue

            thumbnails = result.get("thumbnails", [])

            if not thumbnails:
                continue

            values.append(
                {
                    "id": result["videoId"],
                    "title": result["title"],
                    "artists": result.get("artists", []),
                    "album": result.get("album", {}),
                    "photo": MusicHelper.photo_resize(
                        thumbnails[0]["url"]
                    ),
                }
            )

        values = list(
            {
                value["id"]: value
                for value in values
            }.values()
        )

        if values:

            stmt = insert(Music).values(values)

            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "title": stmt.excluded.title,
                    "artists": stmt.excluded.artists,
                    "album": stmt.excluded.album,
                    "photo": stmt.excluded.photo,
                }
            )

            await db.execute(stmt)
            await db.commit()

        return values

    async def send_search(
        self,
        text: str,
        offset: int = 0
    ):

        inlines = Inlines(self.texts)

        if isinstance(self.data, CallbackQuery):
            chat_id = self.data.message.chat.id
            msg_id = self.data.message.message_id

        else:
            chat_id = self.data.chat.id
            msg_id = self.data.message_id

        sent_msg = await self.bot.send_message(
            chat_id,
            self.texts.load_icon
        )

        song = Song()

        results, has_more = await song.search(
            text,
            offset=offset
        )

        if not results:

            await self.bot.send_message(
                chat_id,
                self.texts.not_found,
                reply_to_message_id=msg_id
            )

            await sent_msg.delete()

            return

        keyboard = inlines.music_search(
            results,
            self.bot_data.info.username,
            text,
            has_more,
            offset
        )

        await self.bot.send_message(
            chat_id,
            self.texts.results,
            reply_to_message_id=msg_id,
            reply_markup=keyboard
        )

        await sent_msg.delete()

        await self.add_result_in_db(
            results,
            self.db
        )

    async def send_start(self, welcome=None):

        if welcome is None:
            welcome = self.texts.welcome

        inlines = Inlines(self.texts)

        if isinstance(self.data, CallbackQuery):
            chat_id = self.data.message.chat.id

        else:
            chat_id = self.data.chat.id

        await self.bot.send_message(
            chat_id,
            welcome,
            reply_markup=inlines.welcome(
                self.bot_data
            )
        )

    @staticmethod
    async def download_file(
        bot: Bot,
        file_id: str,
        user_id: int
    ):

        file_info = await bot.get_file(file_id)

        file_path = file_info.file_path

        os.makedirs(
            "user_files",
            exist_ok=True
        )

        file_extension = "dat"

        hashed_file_id = hashlib.sha256(
            file_id.encode()
        ).hexdigest()[:16]

        file_name = (
            f"{user_id}_"
            f"{hashed_file_id}."
            f"{file_extension}"
        )

        save_path = os.path.join(
            "user_files",
            file_name
        )

        await bot.download_file(
            file_path,
            save_path
        )

        return save_path

    @staticmethod
    async def add_song_in_db(
        db,
        song
    ):

        if not song:
            return None

        thumbnails = song.get(
            "thumbnails",
            []
        )

        if not thumbnails:
            return None

        photo = MusicHelper.photo_resize(
            thumbnails[0]["url"]
        )

        stmt = insert(Music).values(
            id=song["videoId"],
            title=song["title"],
            artists=song.get("artists", []),
            album=song.get("album", {}),
            photo=photo
        ).on_conflict_do_update(
            index_elements=["id"],
            set_={
                "title": song["title"],
                "artists": song.get(
                    "artists",
                    []
                ),
                "album": song.get(
                    "album",
                    {}
                ),
                "photo": photo
            }
        )

        await db.execute(stmt)
        await db.commit()

        return song["videoId"]

    @staticmethod
    async def recognize_file(
        path,
        db
    ):

        try:

            found_song = await Song.recognize(
                path
            )

            if not found_song:
                return None

            if not found_song.get(
                "matches"
            ):
                return None

            track = found_song.get(
                "track"
            )

            if not track:
                return None

            title = track.get(
                "title"
            )

            subtitle = track.get(
                "subtitle"
            )

            if not title:
                return None

            full_name = title

            if subtitle:
                full_name = (
                    f"{title} - {subtitle}"
                )

            song = await Song.get(
                full_name
            )

            if not song:
                return None

            return await HandlersHelper.add_song_in_db(
                db,
                song
            )

        finally:

            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

    async def process_media(
        self,
        media
    ):

        file_id = media.file_id

        is_video = (
            isinstance(media, Video)
            or isinstance(media, VideoNote)
        )

        if is_video:
            limit = config.DOWNLOAD_VIDEO_SIZE_IN_MB
        else:
            limit = config.DOWNLOAD_VOICE_SIZE_IN_MB

        if not limit:
            return await self.data.reply(
                self.bot_data.texts.not_supported
            )

        if not media.file_size:
            return await self.data.reply(
                self.bot_data.texts.unable
            )

        if media.file_size > limit * 1024 * 1024:
            return await self.data.reply(
                self.bot_data.texts.big_file
            )

        msg = await self.data.reply(
            self.bot_data.texts.getting_file
        )

        original_file_path = None
        file_path = None

        try:

            original_file_path = (
                await self.download_file(
                    self.bot,
                    file_id,
                    self.data.from_user.id
                )
            )

            file_path = original_file_path

            if is_video:

                await msg.edit_text(
                    self.bot_data.texts.working_on_file
                )

                file_path = (
                    await Song.extract_audio_from_video(
                        original_file_path
                    )
                )

                original_file_path = None

            await msg.edit_text(
                self.bot_data.texts.finding_music
            )

            song_id = await self.recognize_file(
                file_path,
                self.db
            )

            file_path = None

            if not song_id:
                return await msg.edit_text(
                    self.bot_data.texts.not_found
                )

            await msg.delete()

            await self.send_music_data(
                song_id
            )

        except Exception as e:

            print(
                f"Error processing media: {e}"
            )

            await msg.edit_text(
                self.bot_data.texts.unable
            )

        finally:

            if original_file_path and os.path.exists(
                original_file_path
            ):
                try:
                    os.remove(
                        original_file_path
                    )
                except Exception:
                    pass

            if file_path and os.path.exists(
                file_path
            ):
                try:
                    os.remove(
                        file_path
                    )
                except Exception:
                    pass

    @staticmethod
    async def process_query(
        query: InlineQuery,
        bot_data: BotData,
        db: AsyncSession
    ):

        text = query.query.strip()

        inlines = Inlines(
            bot_data.texts
        )

        song = Song()

        results, _ = await song.search(
            text
        )

        if not results:

            return await query.answer(
                [
                    InlineQueryResultArticle(
                        id=secrets.token_hex(8),
                        title=bot_data.texts.not_found,
                        input_message_content=(
                            InputTextMessageContent(
                                message_text=(
                                    bot_data.texts.not_found
                                )
                            )
                        ),
                        reply_markup=(
                            inlines.music_lyrics(
                                None,
                                only_switch=True
                            )
                        )
                    )
                ],
                cache_time=0
            )

        results = await HandlersHelper.add_result_in_db(
            results,
            db
        )

        audio_results = []

        for song in results:

            performer = ", ".join(
                artist["name"]
                for artist in song["artists"]
            )

            thumbnail_url = song["photo"]

            document = InlineQueryResultArticle(
                id=f"song:{song['id']}",
                title=song["title"],
                thumbnail_url=thumbnail_url,
                description=performer,
                input_message_content=(
                    InputTextMessageContent(
                        message_text=(
                            bot_data.texts.loading
                        )
                    )
                ),
                reply_markup=(
                    inlines.music_lyrics(
                        None,
                        only_switch=True
                    )
                )
            )

            audio_results.append(
                document
            )

        await query.answer(
            audio_results
        )

    @staticmethod
    def is_valid_url(text):

        if not text:
            return False

        pattern = (
            r"^https://"
            r"[a-zA-Z0-9.-]+\."
            r"[a-zA-Z]{2,}"
            r"(/.*)?$"
        )

        return bool(
            re.match(
                pattern,
                text.strip()
            )
        )

    @staticmethod
    def extract_platform_and_id(
        url: str
    ):

        patterns = [
            (
                r"https://music\.apple\.com/"
                r".*/album/.*/\d+\?i=(\d+)",
                "i"
            ),
            (
                r"https://geo\.music\.apple\.com/"
                r".*/album/.*/\d+\?i=(\d+)",
                "i"
            ),
            (
                r"https://open\.spotify\.com/"
                r"track/([a-zA-Z0-9_-]+)",
                "s"
            ),
            (
                r"https://www\.pandora\.com/"
                r"track/([a-zA-Z0-9_-]+)",
                "p"
            ),
            (
                r"https://www\.deezer\.com/"
                r".*/track/(\d+)",
                "d"
            ),
            (
                r"https://soundcloud\.com/"
                r".*/([a-zA-Z0-9_-]+)",
                "sc"
            ),
            (
                r"https://music\.amazon\."
                r".*/albums?/([A-Z0-9]+)",
                "a"
            ),
            (
                r"https://tidal\.com/"
                r"browse/track/(\d+)",
                "t"
            ),
            (
                r"https://us\.napster\.com/"
                r"track/([a-zA-Z0-9_-]+)",
                "n"
            ),
            (
                r"https://music\.yandex\."
                r".*/album/\d+/track/(\d+)",
                "ya"
            ),
            (
                r"https://audiomack\.com/"
                r".*/song/([a-zA-Z0-9_-]+)",
                "am"
            ),
            (
                r"https://www\.boomplay\.com/"
                r"songs/(\d+)",
                "bp"
            ),
            (
                r"https://play\.anghami\.com/"
                r"song/([a-zA-Z0-9_-]+)",
                "an"
            )
        ]

        for pattern, platform in patterns:

            match = re.search(
                pattern,
                url
            )

            if match:

                return {
                    "platform": platform,
                    "id": match.group(1)
                }

        return None

    @staticmethod
    async def get_yt(
        song_id,
        platform
    ):

        platforms = {
            "youtube": (
                r'https://www\.youtube\.com/'
                r'watch\?v=([\w-]+)'
            ),
            "apple_music": (
                r'https://geo\.music\.apple\.com'
                r'[^\s"]+'
            ),
            "spotify": (
                r'https://open\.spotify\.com/'
                r'track/[^\s"]+'
            ),
            "soundcloud": (
                r'https://soundcloud\.com/'
                r'[^\s"]+'
            ),
            "title": (
                r'<div class="css-1oiqcyt '
                r'e12n0mv61">(.*?)</div>'
            ),
            "artist": (
                r'<div class="css-1vk2kj9 '
                r'e12n0mv60">(.*?)</div>'
            )
        }

        res = await MusicHelper.get_musics_info(
            platforms,
            platform,
            song_id
        )

        required = [
            res.get("title"),
            res.get("artist")
        ]

        valid_links = any(
            [
                res.get("apple_music"),
                res.get("spotify"),
                res.get("soundcloud"),
            ]
        )

        is_valid = (
            all(required)
            and valid_links
        )

        if not is_valid:
            return None, False

        return (
            f"{res['title']} - {res['artist']}",
            True
        )

    async def url_handler(
        self,
        text,
        user_id
    ):

        link_data = (
            self.extract_platform_and_id(
                text
            )
        )

        if link_data:

            msg = await self.data.reply(
                self.texts.get_contents
            )

            try:

                yt_name, valid = (
                    await self.get_yt(
                        link_data["id"],
                        link_data["platform"]
                    )
                )

                if not valid:
                    await msg.delete()

                    return await self.data.reply(
                        self.texts.not_found
                    )

                song = await Song.get(
                    yt_name
                )

                if not song:
                    await msg.delete()

                    return await self.data.reply(
                        self.texts.not_found
                    )

                song_id = (
                    await self.add_song_in_db(
                        self.db,
                        song
                    )
                )

                await msg.delete()

                if not song_id:
                    return await self.data.reply(
                        self.texts.not_found
                    )

                return await self.send_music_data(
                    song_id
                )

            except Exception as e:

                print(
                    f"URL platform error: {e}"
                )

                try:
                    await msg.delete()
                except Exception:
                    pass

                return await self.data.reply(
                    self.texts.not_found
                )

        msg = await self.data.reply(
            self.texts.get_contents
        )

        path = (
            f"user_files/"
            f"{user_id}_"
            f"{int(time.time())}.m4a"
        )

        try:

            path = await YtDownload.download_audio_from_url(
                text,
                path
            )

            if path is None:
                return await msg.edit_text(
                    self.texts.not_supported
                )

            if not os.path.exists(path):
                return await msg.edit_text(
                    self.texts.unable
                )

            song_id = await self.recognize_file(
                path,
                self.db
            )

            path = None

            if not song_id:
                return await msg.edit_text(
                    self.texts.not_found
                )

            await msg.delete()

            await self.send_music_data(
                song_id
            )

        except Exception as e:

            print(
                f"URL download error: {e}"
            )

            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

            try:
                await msg.edit_text(
                    self.texts.unable
                )
            except Exception:
                pass

    async def download_song(self):

        song_id = (
            self.data.data.split(":")[1]
        )

        result = await self.db.execute(
            select(Music).filter(
                Music.id == song_id
            )
        )

        song = result.scalar_one_or_none()

        inlines = Inlines(
            self.bot_data.texts
        )

        if not song:

            return await self.data.answer(
                self.bot_data.texts.not_found
            )

        caption = (
            self.bot_data.texts.song_music_caption
            .replace(
                "<song_id>",
                song.id
            )
        )

        if song.file_id:

            return await self.data.message.reply_audio(
                song.file_id,
                caption=caption,
                reply_markup=inlines.music_lyrics(
                    song_id
                )
            )

        keyboard = inlines.music_lyrics(
            song_id
        )

        sent_msg = await self.data.message.answer_audio(
            config.LOADING_SONG,
            caption=self.bot_data.texts.song_loading,
            reply_markup=keyboard
        )

        file_path = None

        try:

            file_path = await self.music_download(
                song
            )

            msg = await sent_msg.edit_media(
                media=InputMediaAudio(
                    media=FSInputFile(
                        file_path
                    ),
                    caption=caption,
                    title=song.title,
                    performer=", ".join(
                        artist["name"]
                        for artist in song.artists
                    ),
                    thumbnail=URLInputFile(
                        song.photo
                    )
                ),
                reply_markup=keyboard
            )

            if not msg.audio:
                raise RuntimeError(
                    "Telegram did not return audio information."
                )

            song.file_id = msg.audio.file_id

            await self.db.commit()

        except Exception as e:

            print(
                f"Song download error: {e}"
            )

            try:
                await sent_msg.edit_caption(
                    caption=self.bot_data.texts.unable
                )
            except Exception:
                pass

        finally:

            if file_path and os.path.exists(
                file_path
            ):
                try:
                    os.remove(
                        file_path
                    )
                except Exception:
                    pass

    async def lyrics_maker(
        self,
        song_id
    ):

        result = await self.db.execute(
            select(Music).filter(
                Music.id == song_id
            )
        )

        song = result.scalar_one_or_none()

        if not song:

            await self.data.message.reply(
                self.bot_data.texts.not_found
            )

            return

        msg = await self.data.message.reply(
            self.bot_data.texts.load_icon
        )

        try:

            if song.lyrics:

                lyrics = song.lyrics

            else:

                lyrics = await Song.get_lyrics(
                    song_id
                )

                if lyrics:
                    song.lyrics = lyrics
                    await self.db.commit()

            if not lyrics:

                await msg.edit_text(
                    self.bot_data.texts.no_lyrics
                )

                return

            max_length = 4096

            parts = []

            while len(lyrics) > max_length:

                split_index = (
                    lyrics[:max_length]
                    .rfind("\n")
                )

                if split_index == -1:
                    split_index = max_length

                parts.append(
                    lyrics[:split_index]
                )

                lyrics = (
                    lyrics[split_index:]
                    .strip()
                )

            parts.append(
                lyrics
            )

            await msg.delete()

            return parts

        except Exception as e:

            print(
                f"Lyrics error: {e}"
            )

            await msg.edit_text(
                self.bot_data.texts.no_lyrics
            )

            return