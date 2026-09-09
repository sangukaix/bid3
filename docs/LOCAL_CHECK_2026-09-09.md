> 후속 업데이트: 아래는 최초 점검 당시 기록입니다. 인덱스 복구·모델 연결 및 실제 API 잔액 확인 결과는 [후속 기록](FOLLOWUP_2026-09-09.md)을 확인하세요.

# 개인 노트북 이전 점검 — 2026-09-09

대상: `D:\pp2026\bid3`. 기존 인계 문서의 Bid2와 현재 폴더명 bid3는 같은 코드 계보로 보인다. Git 이력이 없어 원격 저장소와의 정확한 일치 여부는 확인하지 못했다.

## 결론

기본 웹·API와 자동 테스트는 정상이다. 여기서 개발을 이어갈 수 있다. 다만 이전 PC의 경로가 검색 인덱스에 남아 있고, 인덱스 하나의 전문검색 테이블이 손상되어 AI 기능까지 완전히 이전됐다고 볼 수는 없다.

## 실행 환경과 검증

| 점검 | 결과 |
|---|---|
| Python 가상환경 | 학원 PC `C:\Users\Admin\...`를 참조하여 최초 실행 실패. 현재 PC의 Codex 번들 Python 3.12.14로 `venv --upgrade --without-pip` 실행 후 복구 |
| Python 패키지 | requirements.txt의 직접 의존성 버전 일치, `python -m pip check` 통과 |
| Django | `check`, `migrate --check`, `makemigrations --check --dry-run` 통과 |
| 자동 테스트 | 129개 통과, 91.254초. 외부 AI 호출을 모킹하는 테스트가 포함되어 실제 생성 품질을 보장하지 않음 |
| 프론트엔드 | Node.js 24.18.1, `npm run lint` 및 `npm run build` 통과. 빌드의 TypeScript 검사 포함 |
| 빌드 네트워크 | 제한된 도구 환경에서 Google Fonts 연결 실패. 네트워크 접근 허용 후 코드 변경 없이 성공 |
| 실제 HTTP | `/`, `/login`, `/dashBoard/bidList` 200; Django `/api/bids/` 200; 인증 없는 `/api/company-profile/` 401 |
| OpenAI 연결 | 기존 키로 모델 목록 조회 성공. `gpt-4o-mini`, `text-embedding-3-small`, `gpt-5.6-sol`, `gpt-5.6-terra` 목록에 존재 |
| 나라장터 연결 | 공고 1행 조회 요청에서 결과 코드 `00`, 정상 응답. 기존 DB에 수집·저장은 하지 않음 |
| 제안서 미리보기 | 템플릿 5개 모두 존재. PowerPoint로 기본 템플릿을 임시 PDF 13페이지로 새로 변환 성공. 제한된 실행 환경에서는 실패했으나 접근 허용 후 성공 |

OpenAI 실제 추론·임베딩 생성, 업로드 자료의 외부 전송, 새 제안서 전체 생성은 실행하지 않았다. API 모델 목록 접근 성공은 생성 요청의 한도·품질·성공을 보장하지 않는다. 브라우저에서 로그인 후 모든 화면을 클릭하는 종단간 검증도 수행하지 않았다.

## 데이터 보존

- 메인 SQLite `integrity_check`: `ok`, migration `bids.0022`까지 적용.
- 회원 3명, 공고 53,297건, 저장공고 5건, 회사정보 1건, 정성 제안서 3건, 정량 제안서 1건, 채팅 28건.
- 회사 문서·정성/정량 제안서·유사 제안서 모델의 `file`/`generated_file` 참조 6개 모두 실제 파일 존재.
- 공고의 최신 `notice_date`는 2026-08-26. 최신 수집은 별도 실행 필요.
- `server/.env`에 OpenAI·나라장터·Google 키 항목이 존재하지만, 소스에서 확인한 AI 경로는 OpenAI이다. 키 값은 보고서에 기록하지 않음.
- 기존 인계 문서의 “새 DB이므로 재가입” 설명은 이번 복사본에 해당하지 않음. 기존 DB가 옮겨져 있음.

## 후속 작업이 필요한 문제

### 1. 검색 인덱스 원문 경로

Chroma 인덱스 7개 모두 `source` 메타데이터가 학원 PC의 절대 경로를 가리킨다. 인덱스별 참조 파일 7/1/1/1/3/3/1개가 현재 그 경로에 없으며, 모두 현재 `server/media` 아래의 대응 파일이 존재한다.

`chatbot.build_full_page_context()`와 `document_requirements._unique_source_documents()`는 이 경로로 원문 페이지를 다시 읽는다. 이전 경로로 실제 추출 시 0페이지·실패 1건을 확인했다. 따라서 검색 조각으로 대체되어 문맥·요구사항 추출 품질이 낮아질 수 있다.

권장 조치: 인덱스 백업 후 대응 파일 존재를 검증하면서 source를 현재 경로로 옮긴다. 이후 상대 경로를 저장하고 읽을 때 MEDIA_ROOT 기준으로 해석하도록 개선한다. 코드가 버전 정보 없이 인덱스를 재생성하는 경우도 있으므로 캐시 버전 처리와 함께 검토한다. 이번 점검에서는 원본 인덱스를 변경하지 않았다.

### 2. Chroma 전문검색 인덱스 손상

`server/chroma_db/R26BK01618627/chroma.sqlite3`의 `embedding_fulltext_search` FTS5 테이블에서 무결성 오류를 확인했다. 나머지 6개 SQLite 인덱스는 무결성 검사 통과.

임시 복사본에 SQLite FTS `rebuild`를 수행하면 `integrity_check=ok`로 복구되며 임베딩 행 수 30개가 유지되는 것을 확인했다. 원본은 변경하지 않았다. 전체 인덱스 폴더 백업 후 복구하고 Chroma 검색·문서 수를 다시 검증하는 것이 다음 작업이다.

### 3. Git 이력 누락

현재 루트는 Git 저장소가 아니다. 이전 커밋·브랜치·원격 정보는 함께 옮겨지지 않았다. 작업을 본격적으로 이어가기 전에 기존 원격 저장소와 복사본을 비교하여 이력을 복원하거나 새 저장소 기준을 정해야 한다. 기존 파일을 덮어쓰는 clone/reset은 하지 않았다.

### 4. 기존 개발 단계의 한계

제안서 생성은 동기 요청이며 시간 초과·재시도·백그라운드 작업 개선 항목이 기존 TODO에 남아 있다. 인계 문서에는 실제 생성물의 자리표시자·작은 글씨 자동 보정도 미완료로 기록되어 있다. 현재 설정은 DEBUG 등 로컬 개발용이다. 이번 점검은 운영 배포 적합성 감사가 아니다.

## OpenAI 사용 위치와 교체 범위

| 기능 | 현재 코드의 모델·API | 로컬 전환 판단 |
|---|---|---|
| 공고 채팅·적합도 분석 | `gpt-4o-mini`, ChatOpenAI | 우선 비교 평가할 후보 |
| 회사 지식 추출 | 기본 `gpt-4o-mini`, 구조화 출력 | JSON 형식·근거 검증을 갖춰 전환 가능 |
| 문서 전체 요구사항 | 기본 `gpt-5.6-terra`, 구조화 출력 | 필수 항목 누락률 평가 후 전환 |
| 정성·정량 제안서 | 기본 `gpt-5.6-sol`, Responses 및 구조화 출력 | 긴 입력과 다단계 생성이므로 점진적 전환 권장 |
| 사업자등록증 | `gpt-4o-mini`, Files 업로드·Responses·이미지 입력 | 이미지/OCR 전처리와 별도 어댑터 필요 |
| 문서·질문 임베딩 | `text-embedding-3-small` | 생성 모델과 별개. 변경 시 기존 문서를 새 모델로 재임베딩하고 검색 기준 재평가 필요 |
| 요청 시 웹 검색 | Responses의 `web_search` 도구 | OpenAI 유지 또는 별도 검색 서비스 구현 필요 |
| 공고 추천 점수 | Python 규칙 | LLM 교체 불필요 |

관련 코드: `server/bids/services/rag/`, `company_knowledge.py`, `business_registration.py`. 환경변수로 바꿀 수 있는 모델과 코드에 고정된 모델이 혼재한다. OpenAI 주소 하나만 Ollama로 돌리면 임베딩·파일 업로드·웹 검색까지 영향을 받으므로 기능별 클라이언트를 분리하는 방식이 적합하다.

## 이 노트북의 로컬 LLM

Ollama `http://127.0.0.1:11434`가 응답하며 다음 모델이 설치되어 있다. 다른 프로젝트의 비밀 설정을 탐색하지 않고 로컬 서비스의 모델 목록·정보만 조회했다.

| 모델 | 로컬 API가 보고한 기능 | 모델 메타데이터의 문맥 길이 |
|---|---|---|
| `qwen3:14b` | 텍스트 생성, 도구, thinking; Q4_K_M | 40,960 토큰 |
| `gemma4:26b` | 텍스트 생성, vision, 도구, thinking; Q4_K_M | 262,144 토큰 |

메타데이터의 최대 길이는 이 노트북에서 그 길이로 빠르게 실행된다는 뜻이 아니다. 실행 컨텍스트·메모리·긴 한국어 문서에 대한 성능 검증이 필요하다. 위 모델에는 임베딩 capability가 보고되지 않았다.

실제 로컬 추론도 확인했다. 가상의 짧은 한국어 공고에서 명칭과 수행 기간을 JSON schema로 추출했으며 `qwen3:14b`는 5.1초, `gemma4:26b`는 25.5초에 정답을 반환했다. 각 1회, 모델 로딩 포함, 컨텍스트 4,096·출력 한도 128·thinking 비활성 조건이다. 일반적인 속도 비교나 긴 문서 품질 평가로 해석하면 안 된다.

프로젝트에 설치된 `langchain_openai.ChatOpenAI`를 Ollama의 `/v1` 주소에 연결하고 `with_structured_output(..., method='json_schema')`를 적용한 `qwen3:14b` 테스트도 성공했다. 짧은 영문 샘플의 명칭·기간을 13.3초에 정확히 반환했다. 이 검증용 클라이언트는 별도로 생성했으며 프로젝트의 실제 OpenAI 설정은 바꾸지 않았다.

권장 시작점은 하이브리드이다. 로컬 모델에 짧은 공고 질의·회사 자료 추출·초안 정리를 맡겨 평가하고, 기존 OpenAI 임베딩과 긴 제안서·웹 검색·복잡한 요구사항 검토 경로를 우선 유지한다. 품질이 확인된 기능부터 로컬 비중을 늘린다. 민감 문서의 외부 전송을 금지하려는 목적이면 자동 클라우드 fallback을 허용하지 않는 별도 정책이 필요하다.

비교 기준은 한국어 정확도, 출처 일치, 필수 요구사항 누락률, JSON 파싱 성공률, 실제 PPTX 반영, 처리 시간이다. 짧은 샘플 성공만으로 전체 제안서 품질을 판단하면 안 된다.

참고 문서:

- [Ollama OpenAI 호환 API](https://docs.ollama.com/api/openai-compatibility): OpenAI API 일부와 호환.
- [Ollama 구조화 출력](https://docs.ollama.com/capabilities/structured-outputs): JSON schema 기반 출력 지원.
- [OpenAI 웹 검색](https://developers.openai.com/api/docs/guides/tools-web-search): Responses의 내장 검색 도구.
- [OpenAI 구조화 출력](https://developers.openai.com/api/docs/guides/structured-outputs).

## 다시 실행하는 방법

PowerShell 터미널 두 개에서 각각 실행한다. 가상환경 활성화 없이도 다음 명령을 사용할 수 있다.

```powershell
cd D:\pp2026\bid3\server
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

```powershell
cd D:\pp2026\bid3\web
npm.cmd run dev
```

웹 주소는 `http://localhost:3000`. 이미 점검용 서버가 해당 포트에서 실행 중이면 먼저 그 서버를 종료한다. 새 `.env` 예제로 기존 키를 덮어쓰거나 기존 DB를 삭제할 필요는 없다.

이번 변경은 가상환경의 현재 Python 연결 복구와 이 점검 문서 추가이다. 이전 `pyvenv.cfg`는 `server/venv/pyvenv.cfg.school-backup`에 보관했다. 소스·API 키·메인 DB·원본 Chroma에 기능 변경이나 마이그레이션은 적용하지 않았다. 빌드 캐시는 갱신되었다.
