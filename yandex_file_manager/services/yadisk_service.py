import aiohttp

from .cache import CacheService
from .exceptions import InvalidYandexLinkError, OAuthRequiredError, YandexDiskError, DownloadError


class YandexDiskService:
    """
    Сервис для работы с Яндекс.Диском.
    """

    def __init__(self):
        """
        Инициализация сервиса.
        """
        self.base_url = "https://cloud-api.yandex.net/v1/disk/public/resources"

    async def get_file_list(self, public_key: str) -> list[dict]:
        """
        Получение списка файлов и папок по публичной ссылке.

        :param public_key: Публичная ссылка на ресурс Яндекс.Диска.
        :return: Список словарей с информацией о файлах и папках:
            - 'name': Название файла или папки.
            - 'type': Тип файла (документ, медиа, папка).
            - 'id': Идентификатор файла или папки.
        """
        if not self._is_yandex_link(public_key):
            raise InvalidYandexLinkError("Ссылка не относится к Яндекс.Диску", 422)

        file_list = await CacheService.get_cache(public_key)  # Пробуем получить список файла из кэша
        if file_list is None:
            # В кэше списка нет или он устарел
            url = f"{self.base_url}?public_key={public_key}"
            headers = {}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    # Запрашиваем список элементов папки
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('_embedded', {}).get('items', [])

                        # Формируем список файлов и папок и определяет тип (документ, медиа, папка)
                        file_list = []
                        for item in items:
                            name = item['name']
                            item_type = item['type']
                            mime_type = item.get('mime_type', '')

                            if item_type == 'dir':
                                category = 'folder'
                            elif mime_type.startswith('image') or mime_type.startswith('audio') or mime_type.startswith(
                                    'video'):
                                category = 'media'
                            else:
                                category = 'document'
                            file_list.append({'name': name, 'type': category})

                        await CacheService.save_cache(public_key, file_list)  # Сохраняем список в кэше

                    elif response.status == 401:
                        raise OAuthRequiredError("Для этого ресурса требуется авторизация.", 401)
                    elif response.status == 404:
                        raise YandexDiskError("Ошибка! Ссылка не найдена или недоступна.", 404)
                    else:
                        raise RuntimeError(await response.text(), response.status)

        return file_list

    def _is_yandex_link(self, public_key: str) -> bool:
        """
        Проверка, является ли ссылка действительной для Яндекс.Диска.

        :param public_key: Публичная ссылка на ресурс Яндекс.Диска.
        :return: True, если ссылка на Яндекс.Диск, иначе False.
        """
        return "yadi.sk" in public_key or "disk.yandex.ru" in public_key

    async def download_file_from_yandex(self, public_key: str, file_name: str) -> tuple[bytes, str]:
        """
        Асинхронно загружает файл с Яндекс.Диска по публичному ключу и имени файла.

        :param public_key: Публичный ключ папки.
        :param file_name: Имя файла для загрузки.

       :return: Кортеж (содержимое файла, имя файла).
        """
        async with aiohttp.ClientSession() as session:
            # Формируем URL для получения ссылки на скачивание
            url = f"{self.base_url}/download?public_key={public_key}&path=/{file_name}"
            async with session.get(url) as resp:
                # Проверяем наличие файла
                if resp.status == 404:
                    raise DownloadError("Не удалось найти файл", 404)
                # Проверяем авторизацию
                if resp.status == 401:
                    raise DownloadError("Требуется авторизация", 403)
                # Проверяем общий статус ответа
                if resp.status != 200:
                    error_text = await resp.text()
                    raise DownloadError(f"Ошибка Яндекс.Диска: {resp.status} - {error_text}", 502)
                # Извлекаем данные ответа
                data = await resp.json()
                download_url = data.get("href")
                if not download_url:
                    raise DownloadError("Ссылка на скачивание не найдена", 502)

            # Загружаем файл по полученной ссылке
            async with session.get(download_url) as file_resp:
                if file_resp.status != 200:
                    raise DownloadError(f"Не удалось скачать файл: {file_resp.status}", 502)
                file_content = await file_resp.read()

        return file_content, file_name
