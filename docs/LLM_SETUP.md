# PC와 프로젝트별 LLM 설정

## OpenAI 잔액 없이 사용

개인 노트북의 서버는 다음 설정으로 사용합니다. 설정을 바꾼 후 Django를 재시작하세요.

```dotenv
AI_MODE=local
OLLAMA_BASE_URL=http://127.0.0.1:11434
LOCAL_LLM_MODEL=qwen3:14b
CHAT_LOCAL_MODEL=qwen3:14b
LOCAL_VISION_MODEL=gemma4:26b
LOCAL_LLM_CONTEXT=32768
LOCAL_LLM_MAX_OUTPUT=4096
LOCAL_LLM_TIMEOUT=300
LOCAL_VISION_TIMEOUT=300
LOCAL_LLM_KEEP_ALIVE=0
RAG_SEARCH_MODE=keyword
LOCAL_WEB_SEARCH=duckduckgo
```

`AI_MODE=local`은 역할별 openai 설정보다 우선하며, 텍스트 생성과 사업자등록증 처리를 Ollama로 보냅니다. OpenAI SDK·임베딩 호출은 차단하고 문서 검색은 키워드 방식으로 강제합니다. 로컬 추론 실패 시 OpenAI로 자동 재전송하지 않습니다. 설치된 모델과 실행 중인 Ollama가 필요합니다.

- Qwen: 채팅, 회사 지식 추출, 공고 분석, 요구사항 추출, 제안서 전략·작성·수정·검토, 정량서식, 텍스트 PDF 사업자등록증.
- Gemma: 이미지 및 스캔 PDF 사업자등록증. PDF는 최대 5페이지이며 페이지별 결과가 충돌하면 해당 값을 비워 둡니다.
- 검색: 기존 Chroma의 텍스트 또는 새 로컬 텍스트 색인을 사용합니다. 기존 벡터는 보존합니다. 동의어·간접 표현 검색 품질은 벡터 검색과 다를 수 있습니다.
- 웹 참고자료: 사용자가 웹 검색을 요청하면 공개 검색/URL 페이지를 읽습니다. OpenAI 검색 도구를 호출하지 않습니다. 검색 차단 시 실패를 알리며, 공개 URL을 직접 지정할 수 있습니다. `LOCAL_WEB_SEARCH=disabled`로 끌 수 있습니다.

로컬 모드는 **클라우드 AI를 사용하지 않는 설정**입니다. 나라장터 수집, 회사 홈페이지, 명시적인 웹 검색은 인터넷을 사용합니다. Ollama 주소에는 본인이 관리하는 로컬 모델 서버를 지정해야 합니다.

로컬 제안서 전략·페이지 작성은 입력 예산 안에서 관련 원문과 요구사항을 선택합니다. 출처와 선택/미선택 항목 ID를 기록하며, 전체 요구사항 목록은 최종 결과에 별도로 보존합니다. 전체 문서를 반복 요약하지 않습니다. 최종 검토에서는 모든 요구사항을 실제 작성 문구와 나누어 대조하고, 실제 인용문이나 수치가 확인되지 않으면 검토 필요로 남깁니다. 원문 인용 일치가 제출 적합성을 보증하지는 않습니다.

성공한 로컬 구조화 응답은 Git 제외 경로 `media/local_proposal_cache`에 저장합니다. 모델 태그·주소·문맥/출력 설정·출력 스키마·실제 입력이 같을 때 재사용하므로, 중단 후 다시 요청하면 완료한 호출을 재사용할 수 있습니다. 이는 작업 큐나 화면 진행률 기능은 아닙니다. 다른 장문 처리 경로의 요약 캐시는 기존 `media/local_llm_cache`를 사용합니다. 두 캐시에는 비공개 자료가 포함될 수 있습니다.

슬라이드 지시와 대상 위치는 요약하지 않습니다. 상자보다 긴 문구는 해당 위치만 별도로 재작성하고, 정상 문구는 보존합니다. 잘린 접두 문구·미닫힌 괄호·확인 조건 소실을 검사하며, 짧은 표현에서도 세부사항이 빠질 수 있어 전체 요구사항 검토가 필요합니다. 빈칸 안내문을 그대로 복사한 경우에도 해당 칸을 다시 작성합니다. 요약·목표·일정 등에는 명시된 기본 사업조건을 별도로 전달하지만, 수치 반영이나 전체 조건 준수를 보증하지 않습니다. 입력·출력 한도나 수정값 검증 실패는 오류로 반환합니다.

제안서는 로컬에서 한 장씩 기존 텍스트를 작성·수정합니다. 로컬 경로는 자동 페이지 추가·삭제를 지원하지 않아 템플릿 페이지 수가 유지됩니다. 필요한 분량의 템플릿을 먼저 선택하세요. 기본 keep_alive=0은 요청 후 모델을 내려 Qwen/Gemma의 GPU 메모리 경쟁을 줄이지만 로딩 때문에 느립니다. 잠금은 한 Python 프로세스 안에서만 적용되므로 단일 서버 작업을 권장합니다. 대형 제안서는 여러 분 이상 걸릴 수 있으며 작업 큐 전환은 후속 항목입니다.

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

역할은 CHAT, ANALYSIS, COMPANY_KNOWLEDGE, REQUIREMENT, PROPOSAL, QUANTITATIVE, BUSINESS_REGISTRATION입니다. `*_LOCAL_MODEL`은 공통 LOCAL_LLM_MODEL보다 우선합니다. `*_MODEL`은 OpenAI용입니다. 이미지 모델은 LOCAL_VISION_MODEL을 사용합니다.

hybrid에서 `RAG_SEARCH_MODE=vector`는 기존 text-embedding-3-small을 사용합니다. `WEB_SEARCH_PROVIDER=openai`는 기존 OpenAI 웹 검색을 사용합니다. AI_MODE를 생략한 기존 설치는 호환성을 위해 hybrid이며, 예제 설정의 신규 설치는 local입니다.

전역 OPENAI_BASE_URL을 Ollama 주소로 바꾸지 마세요. 클라우드 주소는 별도 BID_OPENAI_BASE_URL로 관리합니다. Codex 구독 한도와 OpenAI API 잔액은 별개입니다.

## 모델 설치와 선택

Ollama에 상위 모델을 추가해도 `model=qwen3:14b` 요청은 계속 14B를 사용합니다. 학원과 개인 PC가 각각 localhost:11434를 쓰면 별개의 서버입니다. 원격으로 같은 서버에 연결하더라도 각 프로젝트에서 요청한 태그를 따릅니다. Git은 모델 가중치나 비공개 .env를 전달하지 않습니다.

개인 노트북은 RTX 4090 Laptop GPU 16GB VRAM, RAM 64GB이며 qwen3:14b와 gemma4:26b가 설치되어 있습니다. 상위 Qwen은 아직 설치·측정하지 않았습니다. 2026-09-09 확인한 공식 파일 크기는 Qwen3 14B 약 9.3GB, 30B 약 19GB, 32B 약 20GB입니다. 상위 모델은 시스템 RAM/CPU 사용으로 느려질 수 있고 컨텍스트 캐시에 추가 메모리가 필요합니다.

계열이 다른 모델의 B 숫자만으로 품질을 비교할 수 없습니다. 현 구성은 Qwen 텍스트와 Gemma 이미지를 사용하며, 향후 상위 모델은 동일한 한국어 공고의 조건 누락·출처 일치·JSON 성공·실제 문서 반영·시간을 비교한 뒤 선택하세요. 같은 태그를 다시 pull하여 모델 내용이 바뀌면 기존 지식·요약 캐시도 재검토해야 합니다.

공식 참고:
- [Ollama Qwen3](https://ollama.com/library/qwen3)
- [Ollama Chat API](https://docs.ollama.com/api/chat)
- [구조화 출력](https://docs.ollama.com/capabilities/structured-outputs)
- [이미지 입력](https://docs.ollama.com/capabilities/vision)
