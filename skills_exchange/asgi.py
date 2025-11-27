"""
ASGI config for skills_exchange project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skills_exchange.settings')

# initialize Django first
django_asgi_app = get_asgi_application()

# import routing lazily
import importlib
core_routing = importlib.import_module("core.routing")

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(
            core_routing.websocket_urlpatterns
        )
    ),
})
