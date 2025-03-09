import json
from django.db import models
from django.utils.timezone import now
from typing import Optional, List


def get_timestamp():
    """
    Получение временной метки
    """
    return int(now().timestamp())


class YandexDiskCache(models.Model):
    """
    Модель для хранения кэша списка файлов публичной папки Яндекс.Диска.

    Атрибуты:
        public_key (str): Публичная ссылка на папку.
        time (int): Временная метка последнего обновления в секундах.
        file_list (str): JSON-строка с сохранённым списком файлов.
    """

    public_key = models.URLField(unique=True, verbose_name="Публичная ссылка")
    time = models.IntegerField(default=get_timestamp(), verbose_name="Временная метка")
    file_list = models.TextField(verbose_name="Список файлов (JSON)")

    def is_recent(self) -> bool:
        """
        Проверяет, актуален ли кэш (не старше 60 секунд).

        :return bool: True, если кэш свежий, иначе False.
        """
        return (int(now().timestamp()) - self.time) < 60

    def get_files(self) -> Optional[List[str]]:
        """
        Возвращает список файлов, если кэш актуален, иначе None.

        :return: Optional[List[str]]: Список файлов или None, если кэш устарел.
        """
        if self.is_recent():
            return json.loads(self.file_list)
        return None

    def __str__(self) -> str:
        return f"Кэш для {self.public_key} (Обновлен: {self.time})"
