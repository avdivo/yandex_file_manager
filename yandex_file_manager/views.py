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

from django.http import JsonResponse
from django.views import View
from django.middleware.csrf import get_token
import json
from typing import Any, Dict

class IndexView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        error_message = kwargs.get('error_message')  # Получаем ошибку из параметров
        context['error_message'] = error_message  # Добавляем ошибку в контекст
        return context


class CatView(TemplateView):
    """
    Асинхронное представление для получения списка файлов
    на Яндекс.Диске по публичной ссылке.
    """
    template_name = 'cat.html'

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
            file_list = await yandex_service.get_file_list(public_key)
            context = self.get_context_data(file_list=file_list, public_key=public_key)
            return self.render_to_response(context)

        except InvalidYandexLinkError:
            return render(request, 'index.html', {'error_message': 'Ошибка! Ссылка не относится к Яндекс.Диску.'})

        except OAuthRequiredError as e:
            request.session['redirect_after_auth'] = request.get_full_path()
            return redirect(e.auth_url)  # Перенаправление на авторизацию

        except YandexDiskError as e:
            return render(request, 'index.html', {'error_message': f'{e}'})

        except Exception as e:
            return render(request, 'index.html', {'error_message': f'Неизвестная ошибка: {e}'})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


import aiohttp
from django.http import HttpResponse
from django.views import View
from django.http import JsonResponse
import json

class DownloadView(View):
    """
    Асинхронный обработчик загрузки файлов с Яндекс.Диска.

    Принимает POST-запрос с параметрами:
    - public_key (str): Публичный ключ для доступа.
    - file_ids (list[str]): Список идентификаторов файлов (всегда 1 файл).

    Возвращает файл или ошибку.
    """

    async def post(self, request, *args, **kwargs):
        try:
            public_key = request.POST.get("public_key", "")
            file_ids = request.POST.getlist("file_ids[]", [])

            if not public_key or not file_ids:
                return JsonResponse({"error": "Missing public_key or file_ids"}, status=400)

            resource_id = file_ids[0]  # Один ID
            print(f"Public Key: {public_key}, Resource ID: {resource_id}")

            async with aiohttp.ClientSession() as session:
                url = f"https://cloud-api.yandex.net/v1/disk/public/resources/download?public_key={public_key}&path=/{resource_id}"
                async with session.get(url) as resp:
                    if resp.status == 401:
                        return JsonResponse({"error": "Authorization required"}, status=403)
                    if resp.status != 200:
                        error_text = await resp.text()
                        return JsonResponse({"error": f"Yandex error: {resp.status} - {error_text}"}, status=502)
                    data = await resp.json()
                    download_url = data.get("href")
                    if not download_url:
                        return JsonResponse({"error": "No download link in response"}, status=502)

                async with session.get(download_url) as file_resp:
                    if file_resp.status != 200:
                        return JsonResponse({"error": f"Download failed: {file_resp.status}"}, status=502)
                    file_content = await file_resp.read()

            return HttpResponse(file_content, content_type='application/octet-stream', headers={
                'Content-Disposition': f'attachment; filename="{resource_id}"'
            })

        except aiohttp.ClientError as e:
            return JsonResponse({"error": f"Network error: {str(e)}"}, status=503)
        except Exception as e:
            return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    async def get(self, request, *args, **kwargs):
        return HttpResponse("Method not allowed", status=405)




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
