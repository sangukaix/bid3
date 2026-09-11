# BID3 — AI비드

나라장터 공고 검색·추천, 회사 자료 관리, 문서 기반 AI 채팅·분석, 입찰 제안서 작성을 제공하는 프로젝트입니다.

- 웹: Next.js 16 / React 19 / TypeScript
- 서버: Django 5.2 / Django REST Framework / SQLite
- 문서 검색: Chroma + OpenAI 임베딩 또는 API 호출 없는 로컬 키워드 검색
- AI: 기능별 OpenAI / Ollama 선택
- 출력: PPTX 제안서, PDF 미리보기, 정량평가 DOCX

## Windows에서 실행

Python 3.12, Node.js, Git을 설치합니다. PPTX 미리보기에는 PowerPoint 또는 LibreOffice가 필요합니다.

```powershell
git clone https://github.com/sangukaix/bid3.git
cd bid3\server
py -3.12 -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
# 기존 .env가 없을 때만 복사합니다.
Copy-Item .env.example .env
# .env에 나라장터 API 키를 입력합니다. 기본 AI_MODE=local은 OpenAI 키가 필요 없습니다.
# Ollama에 qwen3:14b와 gemma4:26b가 설치되어 있어야 합니다. docs/LLM_SETUP.md 참고.
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

다른 터미널:

```powershell
cd bid3\web
npm.cmd ci
# 기존 .env.local이 없을 때만 복사합니다.
Copy-Item .env.example .env.local
npm.cmd run dev
```

웹: http://localhost:3000\
API: http://127.0.0.1:8000/api/bids/

## 검사

```powershell
cd server
.\venv\Scripts\python.exe manage.py check
.\venv\Scripts\python.exe manage.py migrate --check
.\venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\venv\Scripts\python.exe manage.py test --noinput
.\venv\Scripts\python.exe manage.py repair_local_data
```

`web`에서는 `npm.cmd run lint`, `npm.cmd run build`를 실행합니다. 최초 빌드에는 Google Fonts 다운로드를 위한 인터넷 연결이 필요합니다.

## PC 이전

Git에는 코드·기본 템플릿·문서만 올립니다. `.env`, 회원/회사 DB, 업로드 자료, 생성 제안서, 검색 인덱스, 모델 가중치, 가상환경은 포함하지 않습니다.

기존 데이터를 옮기려면 Django를 종료하고 `server/db.sqlite3`, `server/media`, `server/chroma_db`를 함께 복사합니다. API 키는 별도 전달하고 가상환경은 새 PC에서 다시 생성합니다. 기존 DB를 옮겼다면 재가입이나 회사정보 재입력이 필요하지 않습니다.

원문 참조는 `media://...` 형식으로 저장하여 현재 PC의 MEDIA_ROOT 기준으로 읽습니다. 과거 `.../server/media/...` 절대 경로도 해석합니다.

```powershell
# Django를 종료한 상태에서 실행합니다.
cd server
.\venv\Scripts\python.exe manage.py repair_local_data
.\venv\Scripts\python.exe manage.py repair_local_data --apply
```

`--apply`는 루트 `.backups/`에 DB·업로드 자료·전체 인덱스를 먼저 복사한 뒤, 복사본에서 복구 가능한 FTS 인덱스와 문서 참조를 수정합니다. 임베딩 API는 호출하지 않습니다. 백업은 Git에 올라가지 않습니다.

## 모델과 후속 개발

- [PC·프로젝트별 모델 설정](docs/LLM_SETUP.md)
- [로컬 AI 전환 점검 및 한계](docs/LOCAL_AI_2026-09-10.md)
- [30장 템플릿 후속 점검](docs/LOCAL_AI_2026-09-11.md)
- [회사 주장 근거 검토](docs/COMPANY_CLAIM_REVIEW.md)
- [이전 점검 보고서](docs/LOCAL_CHECK_2026-09-09.md)
- [복구·개발 진행 기록](docs/FOLLOWUP_2026-09-09.md)
- [기존 기능·품질 TODO](docs/TODO.md)

이 저장소는 로컬 개발용입니다. 장시간 제안서 생성의 작업 큐 전환, 생성물 품질 보정, 운영 인증·배포 설정 등은 후속 개발 항목입니다.
