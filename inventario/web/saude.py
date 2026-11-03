"""Liveness em memória, antes de sessão/ORM; detalhes ficam sob autenticação."""
import hashlib
import time
from django.conf import settings
from django.core.cache.backends.locmem import LocMemCache
from django.http import JsonResponse
from django.views.decorators.http import require_GET

limite=LocMemCache("sauron-liveness",{"OPTIONS":{"MAX_ENTRIES":4096}})


@require_GET
def liveness(request):
    from inventario.seguranca import ip_cliente
    ip=ip_cliente(request)
    chave=hashlib.sha256(f"{ip}|{int(time.monotonic()//60)}".encode()).hexdigest()
    limite.add(chave,0,timeout=60)
    try:
        total=limite.incr(chave)
    except ValueError:
        total=1
        limite.set(chave,total,timeout=60)
    if total>settings.SAURON_SAUDE_LIMITE_IP:
        resposta=JsonResponse({"status":"limitado"},status=429)
        resposta["Retry-After"]="60"
    else:
        resposta=JsonResponse({"status":"ok"})
    resposta["Cache-Control"]="no-store"
    return resposta


class LivenessMiddleware:
    def __init__(self,get_response):
        self.get_response=get_response

    def __call__(self,request):
        if request.path=="/api/saude/":
            from inventario.seguranca import AutoriaECabecalhosMiddleware
            resposta=liveness(request)
            resposta["Content-Security-Policy"]=AutoriaECabecalhosMiddleware.CSP
            return resposta
        return self.get_response(request)

