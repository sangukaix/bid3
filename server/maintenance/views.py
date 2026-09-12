import os
import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from .routing import read_config, defaults, save_config, ROLES

@api_view(["GET","PUT"])
@permission_classes([IsAdminUser])
def routing(request):
    try:
        config=read_config()
        if request.method=="PUT":
            config=save_config(request.data,request.user.username)
        return Response({"config":config or defaults(),"saved":config is not None,"roles":ROLES,
                         "openai_key_configured":bool(os.getenv("OPENAI_API_KEY")),
                         "note":"자동 폴백 없음. 키워드 검색·공개 웹 조회는 유지합니다. OpenAI 잔액은 확인하지 않습니다."})
    except ValueError as error:
        return Response({"error":str(error)},status=400)

@api_view(["GET"])
@permission_classes([IsAdminUser])
def status(request):
    try:
        response=requests.get(os.getenv("OLLAMA_BASE_URL","http://127.0.0.1:11434").rstrip("/")+"/api/tags",timeout=(3,5))
        response.raise_for_status()
        models=[m["name"] for m in response.json().get("models",[]) if isinstance(m.get("name"),str)]
        return Response({"ollama_reachable":True,"models":models,
            "openai":"키 등록됨 · 잔액/실행 미확인" if os.getenv("OPENAI_API_KEY") else "키 없음"})
    except (requests.RequestException,ValueError,KeyError):
        return Response({"ollama_reachable":False,"models":[],"openai":"실행 미확인"})
