# PC와 프로젝트별 LLM 설정

## OpenAI 잔액 없이 사용

2026-10-10 개인 노트북은 유지보수 페이지에 저장된 로컬 전용·Gemma4:26b 설정을 사용합니다. 저장된 `.local/ai-routing.json`이 역할별 `.env`보다 우선합니다. 새 환경에서 같은 기본값을 사용하려면 다음과 같이 설정하세요. `.env`를 바꾼 후 Django를 재시작하세요.

```dotenv
AI_MODE=local
OLLAMA_BASE_URL=http://127.0.0.1:11434
LOCAL_LLM_MODEL=gemma4:26b
CHAT_LOCAL_MODEL=gemma4:26b
LOCAL_VISION_MODEL=gemma4:26b
PRESENTATION_LOCAL_MODEL=gemma4:26b
LOCAL_LLM_CONTEXT=32768
LOCAL_LLM_MAX_OUTPUT=4096
LOCAL_LLM_TIMEOUT=300
LOCAL_VISION_TIMEOUT=300
LOCAL_LLM_KEEP_ALIVE=0
PROPOSAL_LLM_KEEP_ALIVE=1m
RAG_SEARCH_MODE=keyword
LOCAL_WEB_SEARCH=duckduckgo
```

`AI_MODE=local`은 역할별 openai 설정보다 우선하며, 텍스트 생성과 사업자등록증 처리를 Ollama로 보냅니다. OpenAI SDK·임베딩 호출은 차단하고 문서 검색은 키워드 방식으로 강제합니다. 로컬 추론 실패 시 OpenAI로 자동 재전송하지 않습니다. 설치된 모델과 실행 중인 Ollama가 필요합니다.

- 텍스트: 채팅, 회사 지식 추출, 공고 분석, 요구사항 추출, 제안서 전략·작성·수정·검토, 정량서식, 텍스트 PDF 사업자등록증. 현재는 Gemma4:26b이며 유지보수 페이지에서 작업별 모델을 선택합니다.
- 이미지: 이미지 및 스캔 PDF 사업자등록증. 현재는 Gemma4:26b입니다. PDF는 최대 5페이지이며 페이지별 결과가 충돌하면 해당 값을 비워 둡니다.
- 검색: 기존 Chroma의 텍스트 또는 새 로컬 텍스트 색인을 사용합니다. 기존 벡터는 보존합니다. 동의어·간접 표현 검색 품질은 벡터 검색과 다를 수 있습니다.
- 웹 참고자료: 사용자가 웹 검색을 요청하면 공개 검색/URL 페이지를 읽습니다. OpenAI 검색 도구를 호출하지 않습니다. 검색 차단 시 실패를 알리며, 공개 URL을 직접 지정할 수 있습니다. `LOCAL_WEB_SEARCH=disabled`로 끌 수 있습니다.

로컬 모드는 **클라우드 AI를 사용하지 않는 설정**입니다. 나라장터 수집, 회사 홈페이지, 명시적인 웹 검색은 인터넷을 사용합니다. Ollama 주소에는 본인이 관리하는 로컬 모델 서버를 지정해야 합니다.

로컬 제안서 전략·페이지 작성은 입력 예산 안에서 관련 원문과 요구사항을 선택합니다. 출처와 선택/미선택 항목 ID를 기록하며, 전체 요구사항 목록은 최종 결과에 별도로 보존합니다. 전체 문서를 반복 요약하지 않습니다. 최종 검토에서는 모든 요구사항을 실제 작성 문구와 나누어 대조하고, 실제 인용문이나 수치가 확인되지 않으면 검토 필요로 남깁니다. 원문 인용 일치가 제출 적합성을 보증하지는 않습니다.

성공한 로컬 구조화 응답은 Git 제외 경로 `media/local_proposal_cache`에 저장합니다. 모델 태그·주소·문맥/출력 설정·출력 스키마·실제 입력이 같을 때 재사용하므로, 중단 후 다시 요청하면 완료한 호출을 재사용할 수 있습니다. 이는 작업 큐나 화면 진행률 기능은 아닙니다. 다른 장문 처리 경로의 요약 캐시는 기존 `media/local_llm_cache`를 사용합니다. 두 캐시에는 비공개 자료가 포함될 수 있습니다.

슬라이드 지시와 대상 위치는 요약하지 않습니다. 상자보다 긴 문구는 해당 위치만 별도로 재작성하고, 정상 문구는 보존합니다. 잘린 접두 문구·미닫힌 괄호·확인 조건 소실을 검사하며, 짧은 표현에서도 세부사항이 빠질 수 있어 전체 요구사항 검토가 필요합니다. 빈칸 안내문을 그대로 복사한 경우에도 해당 칸을 다시 작성합니다. 요약·목표·일정 등에는 명시된 기본 사업조건을 별도로 전달하지만, 수치 반영이나 전체 조건 준수를 보증하지 않습니다. 입력·출력 한도나 수정값 검증 실패는 오류로 반환합니다.

입찰 제안서는 로컬에서 한 장씩 기존 텍스트를 작성·수정합니다. 로컬 입찰 경로는 자동 페이지 추가·삭제를 지원하지 않아 템플릿 페이지 수가 유지됩니다. 필요한 분량의 템플릿을 먼저 선택하세요. 일반 발표자료 작업실의 이어 만들기는 별도 기능입니다. 일반 호출의 기본 keep_alive=0은 요청 후 모델을 내려 GPU 메모리 경쟁을 줄이지만 로딩 때문에 느립니다. 긴 입찰 worker 안에서만 `PROPOSAL_LLM_KEEP_ALIVE`를 적용하며 기본은 `1m`입니다. 마지막 호출 뒤 1분간 유휴 상태이면 모델이 내려갑니다. 작업 컨텍스트 종료 시 호출 설정은 복원되며 일반 채팅·발표자료·다른 프로젝트의 설정은 바꾸지 않습니다. 메모리 반환을 우선하려면 `PROPOSAL_LLM_KEEP_ALIVE=0`으로 설정하세요. 잠금은 한 Python 프로세스 안에서만 적용되므로 서로 다른 프로젝트의 대형 AI 작업을 동시에 실행하지 않는 편이 좋습니다. 입찰 생성·전체 검수는 DB 작업 기록과 별도 로컬 worker로 실행하며 재접속 시 진행 단계가 복원됩니다. PC가 꺼지면 계속 처리되지 않으며 분산 큐는 아닙니다. 상세 흐름과 검증 한계는 [제안서 검증 기록](./PROPOSAL_QUALITY_VALIDATION.md)을 참고하세요.

## 하이브리드로 변경

`AI_MODE=hybrid`로 바꾸면 역할별 설정이 적용됩니다. OpenAI 역할에는 별도의 API 잔액이 필요합니다.

```dotenv
AI_MODE=hybrid
CHAT_PROVIDER=ollama
ANALYSIS_PROVIDER=ollama
COMPANY_KNOWLEDGE_PROVIDER=ollama
REQUIREMENT_PROVIDER=ollama
PROPOSAL_PROVIDER=openai
QUANTITATIVE_PROVIDER=ollama
BUSINESS_REGISTRATION_PROVIDER=ollama
RAG_SEARCH_MODE=keyword
WEB_SEARCH_PROVIDER=public
```

텍스트 역할은 CHAT, ANALYSIS, COMPANY_KNOWLEDGE, REQUIREMENT, PROPOSAL, QUANTITATIVE, CLAIM_REVIEW, BUSINESS_REGISTRATION입니다. `*_LOCAL_MODEL`은 공통 LOCAL_LLM_MODEL보다 우선합니다. `*_MODEL`은 OpenAI용입니다. 이미지 모델은 LOCAL_VISION_MODEL을 사용하며 저장된 VISION 경로가 있으면 그 설정을 따릅니다. 저장된 유지보수 설정이 있으면 모드·역할 변경도 해당 페이지에서 수행해야 합니다.

hybrid에서 `RAG_SEARCH_MODE=vector`는 기존 text-embedding-3-small을 사용합니다. `WEB_SEARCH_PROVIDER=openai`는 기존 OpenAI 웹 검색을 사용합니다. AI_MODE를 생략한 기존 설치는 호환성을 위해 hybrid이며, 예제 설정의 신규 설치는 local입니다.

전역 OPENAI_BASE_URL을 Ollama 주소로 바꾸지 마세요. 클라우드 주소는 별도 BID_OPENAI_BASE_URL로 관리합니다. Codex 구독 한도와 OpenAI API 잔액은 별개입니다.

## 모델 설치와 선택

Ollama에 상위 모델을 추가해도 `model=qwen3:14b` 요청은 계속 14B를 사용합니다. 학원과 개인 PC가 각각 localhost:11434를 쓰면 별개의 서버입니다. 원격으로 같은 서버에 연결하더라도 각 프로젝트에서 요청한 태그를 따릅니다. Git은 모델 가중치나 비공개 .env를 전달하지 않습니다.

개인 노트북은 RTX 4090 Laptop GPU 16GB VRAM, RAM 64GB입니다. 2026-09-09 확인 당시 qwen3:14b와 gemma4:26b가 설치되어 있었고 상위 Qwen은 측정하지 않았습니다. 당시 확인한 공식 파일 크기는 Qwen3 14B 약 9.3GB, 30B 약 19GB, 32B 약 20GB입니다. 이 문서의 과거 설치 목록은 현재 Ollama 모델 목록을 대신하지 않습니다. 상위 모델은 시스템 RAM/CPU 사용으로 느려질 수 있고 컨텍스트 캐시에 추가 메모리가 필요합니다.

계열이 다른 모델의 B 숫자만으로 품질을 비교할 수 없습니다. 현 구성은 텍스트·이미지 모두 Gemma4:26b를 사용합니다. 다른 모델은 동일한 한국어 공고의 조건 누락·출처 일치·JSON 성공·실제 문서 반영·시간을 비교한 뒤 선택하세요. 같은 태그를 다시 pull하여 모델 내용이 바뀌면 기존 지식·요약 캐시도 재검토해야 합니다.

공식 참고:
- [Ollama Qwen3](https://ollama.com/library/qwen3)
- [Ollama Chat API](https://docs.ollama.com/api/chat)
- [구조화 출력](https://docs.ollama.com/capabilities/structured-outputs)
- [이미지 입력](https://docs.ollama.com/capabilities/vision)
