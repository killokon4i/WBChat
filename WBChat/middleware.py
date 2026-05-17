from django.http import Http404
from django.shortcuts import render
from django.conf import settings


class ForceUTF8HtmlCharsetMiddleware:
    """
    Явно добавляет charset=utf-8 к HTML-ответам.
    Иначе при text/html без charset браузер на русской Windows часто берёт windows-1251
    и UTF-8 из шаблона выглядит как «Р“Р»Р°РІРЅР°СЏ».
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        ct = response.get("Content-Type") or ""
        if not ct:
            return response
        main = ct.split(";")[0].strip().lower()
        if main == "text/html" and "charset=" not in ct.lower():
            response["Content-Type"] = "text/html; charset=utf-8"
        return response


class Custom404Middleware:
    """Show styled 404/403 page even when DEBUG=True."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if response.status_code == 404 and settings.DEBUG:
            return render(request, 'errors/404.html', status=404)
        if response.status_code == 403 and settings.DEBUG:
            return render(request, 'errors/403.html', status=403)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, Http404):
            return render(request, 'errors/404.html', status=404)
        return None
