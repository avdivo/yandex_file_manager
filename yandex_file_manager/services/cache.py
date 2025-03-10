import json
from typing import Optional, List
from django.core.cache import cache
from django.utils.timezone import now

class CacheService:
    CACHE_TIMEOUT = 60  # Время в секундах, после которого данные считаются устаревшими

    @staticmethod
    async def get_cache(public_key: str) -> Optional[List[dict]]:
        """
        Получает кэшированные файлы по public_key, если кэш актуален.

        :param public_key: Публичный ключ (ссылка на папку Яндекс.Диска).
        :return: Список файлов или None, если кэша нет или он устарел.
        """
        cache_key = f'yandex_disk_{public_key}'
        cached_data = cache.get(cache_key)

        if cached_data:
            data, timestamp = json.loads(cached_data)
            if (now().timestamp() - timestamp) < CacheService.CACHE_TIMEOUT:
                return data
        return None

    @staticmethod
    async def save_cache(public_key: str, file_list: List[dict]):
        """
        Сохраняет или обновляет список файлов в кэше.

        :param public_key: Публичный ключ (ссылка на папку Яндекс.Диска).
        :param file_list: Список файлов для сохранения.
        """
        cache_key = f'yandex_disk_{public_key}'
        cache.set(cache_key, json.dumps((file_list, now().timestamp())), timeout=CacheService.CACHE_TIMEOUT)
