class YandexDiskError(Exception):
    """Общее исключение для работы с Яндекс.Диском."""
    pass


class InvalidYandexLinkError(YandexDiskError):
    """Исключение, если ссылка не относится к Яндекс.Диску."""
    pass


class OAuthRequiredError(Exception):
    """Исключение, если требуется OAuth-авторизация."""

    def __init__(self, auth_url: str):
        self.auth_url = auth_url
        super().__init__("Для доступа требуется OAuth-авторизация.")
