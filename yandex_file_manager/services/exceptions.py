class YandexDiskError(Exception):
    """Общее исключение для работы с Яндекс.Диском."""

    def __init__(self, message, status):
        self.message = message
        self.status = status
        super().__init__(self.message)


class InvalidYandexLinkError(YandexDiskError):
    """Исключение, если ссылка не относится к Яндекс.Диску."""
    pass


class OAuthRequiredError(YandexDiskError):
    """Исключение, если требуется OAuth-авторизация."""
    pass


class DownloadError(YandexDiskError):
    """Базовый класс для ошибок загрузки."""
    pass
