# PC와 프로젝트별 LLM 설정

## 설치와 선택은 별개입니다

Ollama에는 여러 모델을 함께 설치할 수 있습니다. 요청이 `model=qwen3:14b`이면 그 모델이 실행됩니다. `qwen3:32b`를 추가 설치해도 기존 요청은 바뀌지 않습니다.

- 학원과 집이 각각 `localhost:11434`를 쓰면 서로 다른 PC의 서버입니다. 집에 설치한 모델이 학원에 자동 설치되지 않습니다.
- 학원 프로젝트가 집의 원격 Ollama 서버에 연결한다면 집 모델을 사용할 수 있지만, 여전히 요청에 지정된 모델명을 따릅니다.
- GitHub는 소스를 전달합니다. 모델 가중치와 Git에서 제외한 `.env`는 전달하지 않습니다.
- 정확한 모델 태그를 사용하면 의도하지 않은 선택 변경을 줄일 수 있습니다. 같은 태그를 다시 pull하면 그 태그의 내용은 갱신될 수 있습니다.

## 하이브리드 설정

각 PC의 `server/.env`에 추가하고 Django를 재시작합니다. 아래는 채팅만 로컬로 실행하는 시작 구성입니다. 소스코드의 기본값은 기존 OpenAI 구성을 유지합니다.

```dotenv
OLLAMA_BASE_URL=http://127.0.0.1:11434
LOCAL_LLM_MODEL=qwen3:14b
LOCAL_LLM_CONTEXT=16384
LOCAL_LLM_TIMEOUT=180

CHAT_PROVIDER=ollama
RAG_SEARCH_MODE=keyword
CHAT_LOCAL_MODEL=qwen3:14b
ANALYSIS_PROVIDER=openai
COMPANY_KNOWLEDGE_PROVIDER=openai
REQUIREMENT_PROVIDER=openai
PROPOSAL_PROVIDER=openai
QUANTITATIVE_PROVIDER=openai

OPENAI_TIMEOUT=180
OPENAI_MAX_RETRIES=1
```

`*_LOCAL_MODEL`은 `LOCAL_LLM_MODEL`보다 우선합니다. 학원에서 `CHAT_LOCAL_MODEL=qwen3:14b`, 개인 PC에서는 검증된 상위 모델을 별도로 지정할 수 있습니다. 다른 프로젝트의 모델 설정은 변경되지 않습니다.

지원 텍스트 역할은 CHAT, ANALYSIS, COMPANY_KNOWLEDGE, REQUIREMENT, PROPOSAL, QUANTITATIVE입니다. `*_PROVIDER`는 openai 또는 ollama입니다. `*_MODEL`은 클라우드용, `*_LOCAL_MODEL`은 로컬용입니다. QUANTITATIVE_MODEL 미지정 시 기존 PROPOSAL_MODEL 설정을 기본값으로 사용합니다.

코드는 Ollama native API를 사용해 요청마다 컨텍스트와 출력 한도를 지정하고 thinking을 비활성화합니다. JSON은 Pydantic 스키마로 검증합니다. 로컬 모델 실패 시 OpenAI로 자동 재전송하지 않습니다.

긴 공고 채팅은 로컬 문맥 한도에 맞춰 전달 문맥을 줄입니다. UTF-8 바이트 기반의 보수적 상한을 추가로 검사하여 문서 앞부분이 조용히 잘리는 일을 방지합니다. 긴 제안서 등에서 입력 한도 오류가 나면 문서를 분할하거나 하드웨어에 맞는 더 큰 컨텍스트 설정을 검증해야 합니다. 입력 창이 크다고 정확도나 속도가 보장되는 것은 아닙니다.

## API 잔액 없이 사용하는 문서 검색

`RAG_SEARCH_MODE=keyword`를 지정하면 기존 Chroma에서 텍스트와 출처를 읽거나 새 문서를 로컬 텍스트 색인으로 저장합니다. 한국어 부분 단어를 보완한 BM25 방식으로 검색하므로 질문 임베딩 API를 호출하지 않습니다. 기존 벡터는 삭제하거나 다른 차원의 벡터로 덮어쓰지 않습니다. `text_chunks.json`은 문서 내용이므로 Git에서 제외된 chroma_db 안에만 저장합니다.

`RAG_SEARCH_MODE=vector`로 되돌리면 기존 OpenAI 임베딩 검색을 사용합니다. 키워드 검색은 의미 기반 검색보다 동의어·간접 표현 검색에 약할 수 있으므로 출처와 검색 결과를 확인하세요. 로컬 모델과 키워드 검색만으로 모든 AI 기능이 자동으로 로컬 전환되지는 않습니다.

2026-09-09 실제 OpenAI 임베딩 호출은 429 `credit_balance_exhausted`로 실패했습니다. Codex 구독 한도와 별개인 API 잔액 문제입니다. 현재 개인 노트북의 bid3는 CHAT_PROVIDER=ollama, CHAT_LOCAL_MODEL=qwen3:14b, RAG_SEARCH_MODE=keyword로 설정했습니다. 실제 공고에서 로컬 답변과 출처 표시를 확인했습니다. 분석·정성/정량 제안서 등 클라우드 역할은 별도의 API 잔액이 필요합니다.

## OpenAI로 유지하는 기능

- 벡터 모드의 임베딩: `text-embedding-3-small`. 기존 Chroma와 일치시키기 위해 유지합니다. 교체 시 전체 재임베딩과 검색 기준 재검증이 필요합니다.
- 사업자등록증: 기존 이미지/PDF 처리 경로.
- 명시적인 웹 검색: 별도 OpenAI Responses 도구. WEB_SEARCH_MODEL로 클라우드 모델을 지정합니다.

전역 OPENAI_BASE_URL을 Ollama 주소로 바꾸지 마세요. 이 프로젝트는 별도 BID_OPENAI_BASE_URL을 사용하여 클라우드 키·임베딩·웹 검색과 로컬 생성을 분리합니다. 모든 외부 전송을 금지하는 완전 로컬 모드는 아직 구현하지 않았습니다.

## 상위 Qwen 모델

2026-09-09 확인한 개인 노트북: RTX 4090 Laptop GPU 약 16GB VRAM, RAM 약 64GB. 기존 설치 모델은 qwen3:14b와 gemma4:26b입니다.

Ollama 공식 배포 파일은 qwen3:14b 약 9.3GB, qwen3:30b 약 19GB, qwen3:32b 약 20GB입니다. 파일 크기와 실제 실행 메모리는 다르고 컨텍스트 캐시·동시 작업에 추가 메모리가 필요합니다. 30B/32B는 16GB VRAM을 넘어 시스템 RAM/CPU를 사용할 가능성이 크며 속도가 떨어질 수 있습니다. 이 PC에서 상위 모델은 아직 설치·측정하지 않았습니다.

서로 다른 계열의 B 숫자만으로 품질을 비교할 수 없습니다. MoE는 전체 파라미터와 토큰마다 활성화되는 파라미터도 다릅니다. 기존 모델을 보존한 채 동일한 한국어 공고에서 필수 조건 누락, 출처 일치, JSON 성공률, PPTX 반영, 메모리·응답 시간을 비교한 후 역할별로 선택하는 것을 권장합니다.

초기 짧은 한국어 JSON 추출 테스트는 Qwen14B 5.1초, Gemma26B 25.5초였습니다. 각 1회, 로딩 포함, 컨텍스트 4096·thinking 비활성 조건으로 일반적인 성능 순위가 아닙니다.

공식 참고:
- [Ollama Qwen3 모델 목록](https://ollama.com/library/qwen3)
- [OpenAI API 호환 범위](https://docs.ollama.com/api/openai-compatibility)
- [Ollama 구조화 출력](https://docs.ollama.com/capabilities/structured-outputs)
