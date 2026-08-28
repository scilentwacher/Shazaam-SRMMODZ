from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import urllib.parse


class Inlines:

    def __init__(self, texts):
        self.data = texts

    # =========================================================
    # LANGUAGE
    # =========================================================

    def lang(self):
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🇺🇸 English",
                        callback_data="lang:en"
                    ),
                    InlineKeyboardButton(
                        text="🇷🇺 Русский",
                        callback_data="lang:ru"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🇺🇦 Українська",
                        callback_data="lang:uk"
                    ),
                    InlineKeyboardButton(
                        text="🇪🇸 Español",
                        callback_data="lang:es"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🇺🇿 O‘zbekcha",
                        callback_data="lang:uz"
                    ),
                    InlineKeyboardButton(
                        text="🇧🇷 Português",
                        callback_data="lang:pt"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🇩🇪 Deutsch",
                        callback_data="lang:de"
                    ),
                    InlineKeyboardButton(
                        text="🇮🇹 Italiano",
                        callback_data="lang:it"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🇫🇷 Français",
                        callback_data="lang:fr"
                    ),
                    InlineKeyboardButton(
                        text="🇹🇷 Türkçe",
                        callback_data="lang:tr"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🇮🇱 עברית",
                        callback_data="lang:he"
                    ),
                    InlineKeyboardButton(
                        text="🇸🇦 العربية",
                        callback_data="lang:ar"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🇮🇷 فارسی",
                        callback_data="lang:fa"
                    ),
                    InlineKeyboardButton(
                        text="🇨🇳 中文",
                        callback_data="lang:zh"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🇮🇩 Bahasa Indonesia",
                        callback_data="lang:id"
                    ),
                    InlineKeyboardButton(
                        text="🇸🇪 Svenska",
                        callback_data="lang:sv"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🇲🇾 Bahasa Melayu",
                        callback_data="lang:ms"
                    ),
                    InlineKeyboardButton(
                        text="🇳🇱 Nederlands",
                        callback_data="lang:nl"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🇮🇳 हिंदी",
                        callback_data="lang:hi"
                    ),
                    InlineKeyboardButton(
                        text="🇰🇷 한국어",
                        callback_data="lang:ko"
                    )
                ]
            ]
        )

    # =========================================================
    # WELCOME
    # =========================================================

    def welcome(self, bot):
        username = bot.info.username

        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=self.data.inline_search,
                        switch_inline_query_current_chat=""
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=self.data.add_group,
                        url=f"https://t.me/{username}?startgroup=true"
                    )
                ]
            ]
        )

    # =========================================================
    # MUSIC SEARCH RESULTS
    # =========================================================

    def music_search(
        self,
        results,
        username,
        text="",
        has_more=None,
        offset=0
    ):
        max_button_length = 64

        def shorten_text(text: str, max_length: int) -> str:
            if len(text) > max_length:
                return text[:max_length - 3] + "..."
            return text

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[]
        )

        for result in results:

            artists = result.get("artists", [])

            if artists:
                artist_name = artists[0].get("name", "Unknown")
            else:
                artist_name = "Unknown"

            duration = result.get("duration", "")
            title = result.get("title", "Unknown")

            button_text = shorten_text(
                f"• {duration} • {title} — {artist_name}",
                max_button_length
            )

            video_id = result.get("videoId")

            if not video_id:
                continue

            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=button_text,
                        callback_data=f"song:{video_id}"
                    )
                ]
            )

        # More results button
        if has_more:
            keyboard.inline_keyboard.append(
                [
                    InlineKeyboardButton(
                        text=self.data.more,
                        callback_data=f"search:{offset + 1}"
                    )
                ]
            )

        # Bottom buttons
        keyboard.inline_keyboard.append(
            [
                InlineKeyboardButton(
                    text=self.data.inline_search,
                    switch_inline_query_current_chat=text
                ),
                InlineKeyboardButton(
                    text=self.data.add_group,
                    url=f"https://t.me/{username}?startgroup=true"
                )
            ]
        )

        return keyboard

    # =========================================================
    # MUSIC INFORMATION
    # =========================================================

    def music_data(self, song_id, full_name, links):

        # Make sure links is a dictionary
        if not isinstance(links, dict):
            links = {}

        # Proper URL encoding
        full_name_encoded = urllib.parse.quote_plus(full_name)

        keyboard_buttons = []

        buttons_data = [
            [
                (
                    self.data.audiomack,
                    links.get("audiomack")
                )
            ],
            [
                (
                    self.data.google,
                    f"https://www.google.com/search?q={full_name_encoded}"
                ),
                (
                    self.data.apple_music,
                    links.get("apple_music")
                )
            ],
            [
                (
                    self.data.spotify,
                    links.get("spotify")
                ),
                (
                    self.data.yt,
                    links.get("youtube")
                )
            ],
            [
                (
                    self.data.soundcloud,
                    links.get("soundcloud")
                ),
                (
                    self.data.deezer,
                    links.get("deezer")
                )
            ]
        ]

        for button_group in buttons_data:

            row = []

            for text, url in button_group:

                if url:
                    row.append(
                        InlineKeyboardButton(
                            text=text,
                            url=url
                        )
                    )

            if row:
                keyboard_buttons.append(row)

        # Download button
        keyboard_buttons.append(
            [
                InlineKeyboardButton(
                    text=self.data.receive,
                    callback_data=f"download:{song_id}"
                )
            ]
        )

        return InlineKeyboardMarkup(
            inline_keyboard=keyboard_buttons
        )

    # =========================================================
    # LYRICS / INLINE SEARCH
    # =========================================================

    def music_lyrics(self, song_id, only_switch=False):

        buttons = []

        if not only_switch:
            buttons.append(
                InlineKeyboardButton(
                    text=self.data.lyrics,
                    callback_data=f"lyrics:{song_id}"
                )
            )

        buttons.append(
            InlineKeyboardButton(
                text=self.data.inline_search,
                switch_inline_query_current_chat=""
            )
        )

        return InlineKeyboardMarkup(
            inline_keyboard=[
                buttons
            ]
        )

    # =========================================================
    # GROUP ADMIN PANEL
    # =========================================================

    def group_admin(self, settings: dict):

        if not isinstance(settings, dict):
            settings = {}

        quiet = "✅" if settings.get("quiet") else "❌"
        all_texts = "✅" if settings.get("all_texts") else "❌"
        all_media = "✅" if settings.get("all_media") else "❌"

        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=self.data.language,
                        callback_data="group_lang"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"{quiet} {self.data.queit}",
                        callback_data="group-quiet"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"{all_texts} {self.data.all_texts}",
                        callback_data="group-all_texts"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=f"{all_media} {self.data.all_media}",
                        callback_data="group-all_media"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=self.data.refresh,
                        callback_data="group_refresh"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=self.data.done,
                        callback_data="group_done"
                    )
                ]
            ]
        )

    # =========================================================
    # MAIN ADMIN PANEL
    # =========================================================

    def admin(self):

        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=self.data.stat,
                        callback_data="admin-stat"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=self.data.broadcast,
                        callback_data="admin-broadcast"
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=self.data.done,
                        callback_data="admin-done"
                    )
                ]
            ]
        )

    # =========================================================
    # ADMIN BACK
    # =========================================================

    def admin_back(self):

        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=self.data.back,
                        callback_data="admin-back"
                    )
                ]
            ]
        )