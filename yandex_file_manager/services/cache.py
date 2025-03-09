import json
from django.utils.timezone import now
from typing import Optional, List
from yandex_file_manager.models import YandexDiskCache


class CacheService:
    """
    Сервис для работы с кэшем списка файлов из публичных папок Яндекс.Диска.
    """

    @staticmethod
    def get_cache(public_key: str) -> Optional[List[str]]:
        """
        Получает кэшированные файлы по public_key, если кэш актуален.

        :param public_key: Публичный ключ (ссылка на папку Яндекс.Диска).

        :return Optional[List[str]]: Список файлов или None, если кэша нет или он устарел.
        """
        cache = YandexDiskCache.objects.filter(public_key=public_key).first()
        return cache.get_files() if cache else None

    @staticmethod
    def save_cache(public_key: str, file_list: List[dict]) -> YandexDiskCache:
        """
        Сохраняет или обновляет список файлов в кэше.

        :param public_key: Публичный ключ (ссылка на папку Яндекс.Диска).
        :param file_list: Список файлов для сохранения.

        :return YandexDiskCache: Обновленный объект кэша.
        """
        file_list_json = json.dumps(file_list)
        cache, _ = YandexDiskCache.objects.update_or_create(
            public_key=public_key,
            defaults={"file_list": file_list_json, "time": int(now().timestamp())}
        )
        return cache
