from django.utils.deprecation import MiddlewareMixin


class CorsMiddleware:
    """Allow cross-origin requests from the frontend app with credentials."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            from django.http import HttpResponse
            response = HttpResponse()
        else:
            response = self.get_response(request)

        response["Access-Control-Allow-Origin"] = "http://localhost:5173"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        response["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
        response["Access-Control-Allow-Credentials"] = "true"
        return response


class DisableCSRFForAPI(MiddlewareMixin):
    """Skip CSRF check for /api/ endpoints (frontend sends JSON, not forms)."""

    def process_request(self, request):
        if request.path.startswith("/api/"):
            setattr(request, "_dont_enforce_csrf_checks", True)
