from django.utils import translation
from django.conf import settings


class CookieLocaleMiddleware:
    """Activates language from cookie only; ignores Accept-Language header."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        lang = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME, settings.LANGUAGE_CODE)
        if not translation.check_for_language(lang):
            lang = settings.LANGUAGE_CODE
        translation.activate(lang)
        request.LANGUAGE_CODE = translation.get_language()
        response = self.get_response(request)
        # Don't overwrite the cookie if set_language (or another view) already set it
        if settings.LANGUAGE_COOKIE_NAME not in response.cookies:
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                lang,
                max_age=365 * 24 * 3600,
                httponly=False,
                samesite="Lax",
            )
        return response
