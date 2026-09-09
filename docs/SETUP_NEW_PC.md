# 새 Windows PC에서 Bid2 시작하기

## 0. 학교 컴퓨터를 떠나기 전

집에서 `git pull`로 오늘 작업을 받으려면 학교 컴퓨터의 변경사항을 먼저 GitHub에
올려야 합니다.

```powershell
cd C:\Users\Admin\mbca\bid2
git status
git add --all
git commit -m "작업 내용 요약"
git push origin main
```

`git status`가 `working tree clean`이고, `git log -1 --oneline`의 최신 커밋이
GitHub에도 보이는지 확인합니다. `server/.env`는 절대 `git add`하지 않습니다.

## 1. Git으로 내려오는 것과 내려오지 않는 것

Git으로 내려오는 것:

- Next.js와 Django 소스코드
- DB migration
- 자동 테스트
- Bid2 기본 PPTX 템플릿
- 문서와 `requirements.txt`, `package-lock.json`

Git으로 내려오지 않는 로컬 데이터:

- `server/.env`: 나라장터·OpenAI API Key
- `server/db.sqlite3`: 회원, 회사정보, 저장공고, 추천공고, 채팅, AI 분석
- `server/media/`: 업로드 문서, 공고 첨부파일, 생성 제안서, 미리보기 캐시
- `server/chroma_db/`: 공고 문서 Chunk와 Embedding
- `server/venv/`, `web/node_modules/`: 설치된 패키지

따라서 새 PC에서는 회원가입과 회사정보 입력을 다시 해야 합니다. 학교 컴퓨터의
테스트 데이터를 그대로 쓰려면 위 로컬 파일과 폴더를 별도로 옮겨야 하며 Git만으로는
복구되지 않습니다.

## 2. 먼저 설치할 프로그램

1. Git
2. Python 3.12 64-bit (`Add Python to PATH` 선택)
3. Node.js 20 또는 22 LTS
4. VS Code와 Codex
5. Microsoft PowerPoint 또는 LibreOffice

PowerPoint 또는 LibreOffice는 PPTX 제안서를 PDF와 이미지 미리보기로 변환할 때
필요합니다. 프로그램이 없어도 일부 화면은 열리지만 제안서 미리보기는 만들 수 없습니다.

## 3. 프로젝트 받기

처음 받는 경우:

```powershell
cd 원하는\상위\폴더
git clone https://github.com/sangukaix/bid2.git bid2
cd bid2
```

이미 `bid2`를 clone한 경우:

```powershell
cd bid2
git pull origin main
```

최신 코드 확인:

```powershell
git status
git log -3 --oneline --decorate
```

## 4. Django 백엔드 준비

```powershell
cd server
py -3.12 -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`server/.env`를 열고 본인의 Key만 입력합니다. Key 값은 Git에 올리지 않습니다.

```env
G2B_API_KEY=나라장터_일반인증키
OPENAI_API_KEY=OpenAI_API_Key
PROPOSAL_MODEL=gpt-5.6-sol
REQUIREMENT_MODEL=gpt-5.6-terra
COMPANY_KNOWLEDGE_MODEL=gpt-4o-mini
```

`PROPOSAL_MODEL`은 현재 프로젝트 설정값입니다. OpenAI 계정에서 해당 모델을 사용할 수
없다는 오류가 나오면 임의로 여러 파일을 바꾸지 말고 `.env`의 모델명부터 확인합니다.

DB 생성과 검사:

```powershell
python manage.py migrate
python manage.py check
python manage.py test
```

관리자 계정이 필요할 때만 생성합니다.

```powershell
python manage.py createsuperuser
```

나라장터 시험 수집은 전체 수집 전에 2페이지만 실행합니다.

```powershell
python manage.py sync_bids --max-pages 2
```

백엔드 실행:

```powershell
python manage.py runserver
```

정상 주소:

- Django API: `http://127.0.0.1:8000/api/bids/`
- Django 관리자: `http://127.0.0.1:8000/admin/`

## 5. Next.js 프론트엔드 준비

VS Code에서 새 터미널을 하나 더 열고 실행합니다.

```powershell
cd bid2\web
npm install
Copy-Item .env.example .env.local
npm run dev
```

정상 주소:

- 웹 화면: `http://localhost:3000`

`web/.env.local`에는 서버 컴포넌트용 `BID_API_BASE_URL`과 브라우저용
`NEXT_PUBLIC_API_BASE_URL`이 함께 들어갑니다. 로컬 Django 주소를 바꿀 때 두 값을
같이 수정합니다.

검사 명령:

```powershell
npm run lint
npm run build
```

## 6. 새 DB에서 처음 확인할 순서

```text
회원가입
  -> 로그인
  -> 회사정보 입력
  -> 회사 기본자료·기존 제안서 등록
  -> 나라장터 시험 공고 수집
  -> 공고 저장
  -> AI 채팅
  -> 입찰성공률 분석
  -> 제안서 생성과 미리보기
```

공고 문서의 Chroma DB는 모든 공고를 한꺼번에 만들지 않습니다. 특정 공고에서 AI 기능을
처음 사용할 때 첨부문서를 내려받아 Lazy indexing하며 이후에는 저장된 인덱스를 재사용합니다.

## 7. 자주 발생하는 오류

`npm`이 `package.json`을 찾지 못함:

- 현재 위치가 `bid2\web`인지 확인합니다.

`No module named django`:

- 현재 위치가 `bid2\server`인지 확인하고 venv를 활성화합니다.

프론트에서 `Failed to fetch`:

- Django 서버 `127.0.0.1:8000`이 실행 중인지 확인합니다.

API Key 오류:

- `server/.env` 파일명과 `G2B_API_KEY=`, `OPENAI_API_KEY=` 형식을 확인합니다.
- `G2B_API_KEY=G2B_API_KEY=...`처럼 변수명을 두 번 쓰지 않습니다.

템플릿 미리보기 오류:

- PowerPoint 또는 LibreOffice 설치 여부를 확인합니다.
- 최초 변환은 시간이 걸리며 이후 결과는 `server/media/proposal_template_previews/`에서 재사용합니다.
