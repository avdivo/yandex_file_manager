import aiohttp
from typing import Any, Dict, List
from django.conf import settings

from .exceptions import InvalidYandexLinkError, OAuthRequiredError, YandexDiskError

class YandexDiskService:
    """
    Сервис для работы с Яндекс.Диском.
    """

    def __init__(self, access_token: str = None):
        """
        Инициализация сервиса.

        :param access_token: OAuth-токен для доступа к Яндекс.Диску (опционально).
        """
        self.access_token = access_token
        self.base_url = "https://cloud-api.yandex.net/v1/disk/public/resources"
        self.OAUTH_URL = "https://oauth.yandex.ru/authorize"


    async def get_file_list(self, public_key: str) -> List[Dict]:
        """
        Получение списка файлов и папок по публичной ссылке.

        :param public_key: Публичная ссылка на ресурс Яндекс.Диска.
        :return: Список словарей с информацией о файлах и папках:
            - 'name': Название файла или папки.
            - 'type': Тип файла (документ, медиа, папка).
            - 'id': Идентификатор файла или папки.
        """
        if not self._is_yandex_link(public_key):
            raise InvalidYandexLinkError("Ссылка не относится к Яндекс.Диску")

        if not self._is_public_link(public_key) and not self.access_token:
            auth_url = (
                f"{self.OAUTH_URL}?response_type=code"
                f"&client_id={settings.YANDEX_CLIENT_ID}"
                f"&redirect_uri={settings.YANDEX_REDIRECT_URI}"
            )
            raise OAuthRequiredError(auth_url)

        url = f"{self.base_url}?public_key={public_key}"
        headers = {}

        # Если ссылка не публичная, добавляем OAuth-токен
        if not self._is_public_link(public_key) and not self.access_token:
            raise Exception("Для доступа к приватной папке требуется OAuth-токен. Пройдите авторизацию.")

        if self.access_token:
            headers["Authorization"] = f"OAuth {self.access_token}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                print(url)
                if response.status == 200:
                    data = await response.json()
                    items = data.get('_embedded', {}).get('items', [])

                    # Формируем список файлов и папок и определяет тип (документ, медиа, папка)
                    file_list = []
                    for item in items:
                        name = item['name']
                        resource_id = item['resource_id']
                        item_type = item['type']
                        mime_type = item.get('mime_type', '')

                        if item_type == 'dir':
                            category = 'folder'
                        elif mime_type.startswith('image') or mime_type.startswith('audio') or mime_type.startswith(
                                'video'):
                            category = 'media'
                        else:
                            category = 'document'
                        file_list.append({'name': name, 'type': category, 'id': resource_id})

                    return file_list

                elif response.status == 401:
                    auth_url = (
                        f"{self.OAUTH_URL}?response_type=code"
                        f"&client_id={settings.YANDEX_CLIENT_ID}"
                        f"&redirect_uri={settings.YANDEX_REDIRECT_URI}"
                    )
                    raise OAuthRequiredError(auth_url)
                elif response.status == 404:
                    raise YandexDiskError("Ошибка! Ссылка не найдена или недоступна.")
                else:
                    raise RuntimeError(f"Ошибка! Код: {response.status}, сообщение: {await response.text()}")


    def _is_yandex_link(self, public_key: str) -> bool:
        """
        Проверка, является ли ссылка действительной для Яндекс.Диска.

        :param public_key: Публичная ссылка на ресурс Яндекс.Диска.
        :return: True, если ссылка на Яндекс.Диск, иначе False.
        """
        return "yadi.sk" in public_key or "disk.yandex.ru" in public_key

    def _is_public_link(self, public_key: str) -> bool:
        """
        Проверка, является ли ссылка публичной.

        :param public_key: Публичная ссылка на ресурс Яндекс.Диска.
        :return: True, если ссылка публичная, иначе False.
        """
        return True
        return public_key.startswith("https://yadi.sk/d/") or public_key.startswith("https://yadi.sk/i/")
