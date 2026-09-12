"""Private runtime routing. Saved configuration takes precedence over .env."""
import json
import os
import re
import threading
from pathlib import Path
from uuid import uuid4
from django.conf import settings
LOCK = threading.Lock()
ROLES = {
 "CHAT":"공고 채팅", "ANALYSIS":"공고 분석", "COMPANY_KNOWLEDGE":"회사 자료 추출",
 "REQUIREMENT":"요구사항 추출", "PROPOSAL":"제안서 작성·수정",
 "QUANTITATIVE":"정량서식", "CLAIM_REVIEW":"회사 근거 검토",
 "BUSINESS_REGISTRATION":"사업자등록증 텍스트", "VISION":"사업자등록증 이미지"
}
def config_path():
    return Path(getattr(settings,"MAINTENANCE_ROUTING_PATH",settings.BASE_DIR.parent / ".local" / "ai-routing.json"))
def read_config():
    path=config_path()
    if not path.exists():
        return None
    try:
        return validate(json.loads(path.read_text(encoding="utf-8")))
    except (ValueError, OSError, TypeError, KeyError) as error:
        raise ValueError("관리자 AI 설정을 읽을 수 없습니다. 설정 파일을 확인하세요.") from error
def validate(data):
    if not isinstance(data,dict) or data.get("mode") not in {"local","hybrid"}:
        raise ValueError("mode는 local 또는 hybrid여야 합니다.")
    routes=data.get("routes")
    if not isinstance(routes,dict) or set(routes)!=set(ROLES):
        raise ValueError("모든 작업의 설정이 필요합니다.")
    result={}
    for role,item in routes.items():
        if not isinstance(item,dict) or item.get("provider") not in {"ollama","openai"}:
            raise ValueError("지원하지 않는 provider입니다.")
        model=item.get("model","")
        if not isinstance(model,str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,119}",model):
            raise ValueError("모델 이름을 확인하세요.")
        if item["provider"]=="ollama" and ("cloud" in model.lower() or "/" in model and "://" in model):
            raise ValueError("로컬 모델 태그만 사용할 수 있습니다.")
        if data["mode"]=="local" and item["provider"]!="ollama":
            raise ValueError("로컬 전용 모드에는 OpenAI 작업을 저장할 수 없습니다.")
        result[role]={"provider":item["provider"],"model":model}
    return {"mode":data["mode"],"routes":result}
def defaults():
    return {"mode":"local","routes":{role:{"provider":"ollama","model":
        os.getenv("LOCAL_VISION_MODEL","gemma4:26b") if role=="VISION" else
        os.getenv(f"{role}_LOCAL_MODEL",os.getenv("LOCAL_LLM_MODEL","qwen3:14b"))}
        for role in ROLES}}
def save_config(data, username):
    clean=validate(data)
    with LOCK:
        path=config_path();path.parent.mkdir(parents=True,exist_ok=True)
        previous=path.read_text(encoding="utf-8") if path.exists() else None
        if previous:
            (path.parent / f"ai-routing-backup-{uuid4().hex}.json").write_text(previous,encoding="utf-8")
        temp=path.with_name(f".routing-{uuid4().hex}.json")
        temp.write_text(json.dumps({**clean,"updated_by":username},ensure_ascii=False,indent=2),encoding="utf-8")
        temp.replace(path)
    return clean
def special_route(role):
    config=read_config()
    return config["routes"][role] if config else None
