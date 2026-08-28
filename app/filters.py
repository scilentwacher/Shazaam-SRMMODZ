from aiogram.filters import BaseFilter
from aiogram import types

from app.models import User
from app.utils.bot_data import BotData


class DynamicBotDataFilter(BaseFilter):
    key = "dynamic_condition"

    def __init__(self, dynamic_condition: str):
        self.dynamic_condition = dynamic_condition

    def __call__(self, message: types.Message, **kwargs) -> bool:
        bot_data: BotData = kwargs.get("bot_data")
        user: User = kwargs.get("user")
        
        if not bot_data or not user:
            return False
        
        bot_data.texts.lang = user.lang

        if hasattr(bot_data.texts, self.dynamic_condition):
            expected_value = getattr(bot_data.texts, self.dynamic_condition)
            return message.text == expected_value
        
        return False


class GroupFilter(BaseFilter):
    def __init__(self):
        pass
        
    def __call__(self, obj: types.Message | types.CallbackQuery) -> bool:
        if not isinstance(obj, (types.Message, types.CallbackQuery)):
            return False
        
        chat = obj.chat if isinstance(obj, types.Message) else obj.message.chat
        return chat.type in ["group", "supergroup"]
