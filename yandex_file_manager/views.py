from django.shortcuts import render
from django.http import HttpResponse

from django.shortcuts import render


def index(request):
    """
    Загрузка стартовой страницы
    для запроса публичной ссылки на папку Yandex.Disk.
    """
    return render(request, 'index.html')


def cat_view(request):
    link = request.GET.get('link')
    # Обработка полученной ссылки
    if link:
        return HttpResponse(f"Ссылка получена: {link}")
    return HttpResponse("Ссылка не указана")

