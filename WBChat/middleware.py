from django.http import Http404
from django.shortcuts import render
from django.conf import settings


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
