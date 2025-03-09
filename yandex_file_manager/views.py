from django.views import View
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse

from .services.yadisk_service import YandexDiskService
from .services.exceptions import InvalidYandexLinkError, OAuthRequiredError, YandexDiskError


class IndexView(TemplateView):
    """
    Представление для отображения стартовой страницы.
    """
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        """
        Обработка GET запроса. Возвращает страницу с сообщением.
        :param kwargs:
        :return: index.html
        """
        context = super().get_context_data(**kwargs)
        message = kwargs.get('error_message', 'Пожалуйста, укажите публичную ссылку на папку Yandex.Disk')
        context['message'] = message  # Добавляем ошибку в контекст
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
        :return: cat.html
        """
        # Получаем публичную ссылку из параметров запроса
        public_key = request.GET.get("link")
        if not public_key:
            return render(request, 'index.html', {'error_message': 'Ошибка! Ссылка не может быть пустой.'})

        # Создаем экземпляр сервиса
        yandex_service = YandexDiskService()

        try:
            # Запрашиваем список файлов папки
            file_list = await yandex_service.get_file_list(public_key)
            context = self.get_context_data(file_list=file_list, public_key=public_key)
            return self.render_to_response(context)  # Отображаем страницу

        except InvalidYandexLinkError as e:
            print(e)
            return redirect('index.html', {'error_message': str(e)})

        except OAuthRequiredError as e:
            return render(request, 'index.html', {'error_message': e})

        except YandexDiskError as e:
            return render(request, 'index.html', {'error_message': e})

        except Exception as e:
            return render(request, 'index.html', {'error_message': f'Неизвестная ошибка: {e}'})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class DownloadView(View):
    """
    Асинхронный обработчик загрузки файлов с Яндекс.Диска.
    """

    async def post(self, request, *args, **kwargs):
        """
        Принимает POST-запрос с параметрами:

        :param request:
        :param kwargs: public_key (str): Публичный ключ для доступа.
        :param kwargs: file_ids (list[str]): Список идентификаторов файлов (всегда 1 файл).
        :return: Возвращает файл или ошибку.
        """
        # Извлекаем параметры из запроса
        public_key = request.POST.get("public_key", "")
        file_ids = request.POST.getlist("file_ids[]", [])

        if not public_key or not file_ids:
            return JsonResponse({"error": "Ошибка запроса"}, status=400)

        file_name = file_ids[0]  # Берем только первый файл

        # Создаем экземпляр сервиса
        yandex_service = YandexDiskService()

        try:
            # Получаем файл и имя из сервиса
            file_content, file_name = await yandex_service.download_file_from_yandex(public_key, file_name)
            # Отдаем файл
            return HttpResponse(file_content, content_type='application/octet-stream', headers={
                'Content-Disposition': f'attachment; filename="{file_name}"'
            })

        except Exception as e:
            # Передаем ошибку из сервиса на фронт
            return JsonResponse({"error": str(e)}, status=getattr(e, 'status', 500))

    async def get(self, request, *args, **kwargs):
        return HttpResponse("Method not allowed", status=405)
