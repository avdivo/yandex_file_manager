import aiohttp

from django.shortcuts import render

from django.http import JsonResponse, HttpResponse
from django.views import View
from typing import Any
from django.http import HttpResponse

from django.shortcuts import render

from .services.yadisk_service import YandexDiskService  # Импортируем сервис


from django.views.generic import TemplateView
from django.conf import settings
from django.shortcuts import render, redirect
from django.views import View
from django.http import JsonResponse
from .services.yadisk_service import YandexDiskService  # Импортируем сервис
from .services.exceptions import InvalidYandexLinkError, OAuthRequiredError, YandexDiskError


class IndexView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        error_message = kwargs.get('error_message')  # Получаем ошибку из параметров
        context['error_message'] = error_message  # Добавляем ошибку в контекст
        return context


class CatView(View):
    """
    Асинхронное представление для получения списка файлов
    на Яндекс.Диске по публичной ссылке.
    """

    async def get(self, request, *args, **kwargs):
        """
        Обработка GET-запроса для получения списка файлов и папок на Яндекс.Диске.

        :param request: HTTP-запрос.
        :return: JSON-ответ с результатами или сообщением об ошибке.
        """
        # Получаем публичную ссылку из параметров запроса
        public_key = request.GET.get("link")
        if not public_key:
            return render(request, 'index.html', {'error_message': 'Ошибка! Ссылка не может быть пустой.'})

        # Создаем экземпляр сервиса
        access_token = request.session.get('access_token')  # Получаем OAuth-токен из сессии
        yandex_service = YandexDiskService(access_token)

        try:
            files = await yandex_service.get_file_list(public_key)
            print(files)
            # return render(request, 'cat.html', {'files': files})

        except InvalidYandexLinkError:
            return render(request, 'index.html', {'error_message': 'Ошибка! Ссылка не относится к Яндекс.Диску.'})

        except OAuthRequiredError as e:
            request.session['redirect_after_auth'] = request.get_full_path()
            return redirect(e.auth_url)  # Перенаправление на авторизацию

        except YandexDiskError as e:
            return render(request, 'index.html', {'error_message': f'{e}'})

        except Exception as e:
            return render(request, 'index.html', {'error_message': f'Неизвестная ошибка: {e}'})


class OAuthCallbackView(View):
    """
    Представление для обработки callback от Яндекс.Диска и получения OAuth-токена.
    """
    async def get(self, request, *args, **kwargs):
        # Получаем код авторизации из параметров запроса
        code = request.GET.get("code")
        if not code:
            return render(request, 'index.html', {'error_message': f'Не удалось получить код авторизации.'})


        token_url = "https://oauth.yandex.ru/token"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.YANDEX_CLIENT_ID,
            "client_secret": settings.YANDEX_CLIENT_SECRET,
            "redirect_uri": settings.YANDEX_REDIRECT_URI,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                if response.status == 200:
                    token_data = await response.json()
                    access_token = token_data.get("access_token")

                    if not access_token:
                        return render(request, 'index.html', {'error_message': f'Ошибка получения токена.'})

                    # Сохраняем токен в сессии пользователя
                    request.session['yandex_access_token'] = access_token

                    # Перенаправляем пользователя обратно на исходную страницу
                    redirect_url = request.session.pop('redirect_after_auth', '/')
                    return redirect(redirect_url)

                else:
                    return render(request, 'index.html', {'error_message': f'Ошибка получения токена.'})
