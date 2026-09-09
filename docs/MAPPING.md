# Bid2 구조와 흐름

기준일: 2026-08-22

## 폴더 구조

```text
bid2/
|-- web/                                  # Next.js + React 사용자 화면
|   |-- app/                              # URL별 page.tsx와 layout.tsx
|   |   `-- dashBoard/
|   |       |-- bidList/                  # 나라장터 공고 검색
|   |       |-- recommendedBid/           # 규칙 기반 추천공고
|   |       |-- myCompanyInfo/            # 회사정보
|   |       |-- matchBid/                 # 저장공고와 제안서 프로젝트
|   |       `-- trash/                    # 삭제한 제안서 프로젝트 복원·영구삭제
|   |-- components/
|   |   |-- bids/                         # 공고 필터와 표
|   |   |-- companyForm/                  # 회사정보 입력/조회
|   |   |-- chat/                         # 공고 질문과 제안서 수정 AI비서
|   |   `-- proposal/                     # 생성, 템플릿, 정량자료, 휴지통, 미리보기
|   |-- lib/
|   |   |-- api.ts                        # 브라우저에서 사용하는 Django 공통 주소
|   |   `-- bidFormat.ts                  # 공고 사업비 공통 표시
|   `-- types/                            # Django JSON TypeScript 자료형
|-- server/                               # Django API 서버
|   |-- bids/
|   |   |-- models.py                     # SQLite 테이블 정의
|   |   |-- views.py                      # API 요청 처리
|   |   |-- urls.py                       # API 주소 연결
|   |   |-- services/                     # 수집, 추천, 문서, AI 로직
|   |   |   |-- rag/                      # Chroma, Retriever, 채팅, 분석, 제안서
|   |   |   |   |-- document_requirements.py # 전체 첨부문서 요구사항 목록과 캐시
|   |   |   |   `-- quantitative.py       # 정량평가 요구사항과 작성 가능 항목
|   |   |   |-- company_website.py        # 회사 홈페이지 수집
|   |   |   |-- project_reference.py      # 프로젝트별 유사 제안서 지식
|   |   |   |-- proposal_preview.py       # PPTX 미리보기와 템플릿 이미지
|   |   |   |-- proposal_pptx_renderer.py # 생성 계획을 PPTX에 적용
|   |   |   `-- quantitative_docx.py      # 정량평가 Word 작성안 출력
|   |   `-- tests.py                      # Django 자동 테스트
|   |-- proposal_templates/               # Git에 포함되는 Bid2 PPTX 템플릿
|   |-- media/                            # Git 제외: 업로드/생성/미리보기 파일
|   |-- chroma_db/                        # Git 제외: 공고별 Vector DB
|   `-- db.sqlite3                        # Git 제외: 로컬 사용자와 서비스 데이터
`-- docs/                                 # 설치, 인계, 구조, TODO 문서
```

## 전체 요청 흐름

```text
사용자
  -> Next.js/React 화면 (localhost:3000)
  -> fetch + Token
  -> Django REST API (127.0.0.1:8000)
  -> SQLite / 나라장터 API / Chroma / OpenAI
  -> JSON 또는 파일 응답
  -> React 화면 갱신
```

## 공고 수집과 추천

```text
나라장터 Open API
  -> g2b_api.py
  -> sync_bids.py
  -> BidNotice + raw_data
  -> recommendation.py의 Python 규칙
  -> RecommendedBid
  -> 추천공고 화면
```

추천공고 점수는 OpenAI 낙찰확률이 아니라 키워드, 지역, 공고 유형 등의 조건 일치도입니다.

## AI 채팅

```text
공고에서 AI비서 질문
  -> prepare_docs_for_ai.py가 공고 첨부파일 준비
  -> extract_document.py가 PDF/HWP/HWPX/Word/Excel/PPT/ZIP 등 추출
  -> RecursiveCharacterTextSplitter
  -> OpenAI Embedding
  -> 공고번호별 Chroma 저장 또는 기존 DB 재사용
  -> Retriever가 관련 근거 검색
  -> chatbot.py
  -> 답변 + 파일명/페이지/문서 위치
  -> BidChatMessage 저장
```

## 제안서 생성

```text
회사 프로필 -------------------------------+
회사 기본자료/기존 제안서/홈페이지          |
  -> company_knowledge.py                   |
  -> CompanyKnowledgeItem                   |
                                               v
공고 첨부문서 -> Chroma + 요구사항 목록 -> proposal.py
프로젝트 유사 제안서 ------------------------>
                                      -> 수주 전략
                                      -> 목차와 슬라이드 작성 계획
                                      -> proposal_pptx_renderer.py
                                      -> Bid2 PPTX 템플릿
                                      -> 생성 PPTX
                                      -> PDF 미리보기
                                      -> AI비서 수정
                                      -> 최종 다운로드
```

## 정량평가 작성안

```text
공고 전체 요구사항 + 관련 원문
  -> quantitative.py
  -> 회사 프로필·회사 문서·홈페이지 지식과 대조
  -> 작성 가능 / 자료 필요 / 담당자 확인 구분
  -> quantitative_docx.py
  -> Word 작성안 + 화면의 누락 목록
```

## 제안서 프로젝트 휴지통

```text
프로젝트 삭제
  -> SavedBid.proposal_trashed_at 기록
  -> 휴지통 목록
  -> 복원: 프로젝트 목록 마지막으로 이동
  -> 영구삭제: 제안서·채팅·분석·정량자료·유사 제안서 삭제
  -> 저장한 공고 자체는 유지
```

## 템플릿 미리보기

```text
server/proposal_templates/*.pptx
  -> PowerPoint 또는 LibreOffice로 PDF 변환
  -> pypdfium2로 슬라이드별 PNG 생성
  -> server/media/proposal_template_previews/ 캐시
  -> /api/proposal-templates/{id}/slides/{page}/
  -> TemplateGallery.tsx
  -> 카드 표지 + 세로 보기 + 바둑판 전체 보기
```

## 주요 파일

| 파일 | 역할 |
|---|---|
| `server/bids/models.py` | 회원 연결 데이터, 공고, 추천, 저장, 채팅, 분석, 제안서 DB 모델 |
| `server/bids/views.py` | Next.js 요청을 받아 DB·AI·파일 기능 실행 |
| `server/bids/services/recommendation.py` | 회사조건과 공고의 규칙 기반 점수 계산 |
| `server/bids/services/rag/chatbot.py` | 공고 근거 기반 AI 답변 |
| `server/bids/services/rag/analysis.py` | 공고와 회사의 구조화 분석 |
| `server/bids/services/rag/proposal.py` | 회사 강점·공고 요구사항을 이용한 제안서 계획 |
| `server/bids/services/rag/document_requirements.py` | 모든 첨부문서의 요구사항 추출과 공고별 캐시 |
| `server/bids/services/rag/quantitative.py` | 정량평가 항목과 회사 증빙 대조 |
| `server/bids/services/company_website.py` | 회사 홈페이지를 회사 지식으로 수집 |
| `server/bids/services/project_reference.py` | 현재 프로젝트의 유사 제안서 문맥 생성 |
| `server/bids/services/proposal_pptx_renderer.py` | 작성 계획을 실제 PPTX로 출력 |
| `server/bids/services/proposal_preview.py` | 생성본 PDF와 템플릿 PNG 미리보기 |
| `web/components/proposal/ProposalWorkspace.tsx` | 공고별 제안서 작업 화면 |
| `web/components/proposal/TemplateGallery.tsx` | 템플릿 선택과 팝업 미리보기 |
| `web/components/proposal/ProposalAssistant.tsx` | 제안서 화면의 AI비서 연결 |
| `web/components/proposal/QuantitativeProposalPanel.tsx` | 정량평가 작성·다운로드 화면 |
| `web/components/proposal/ProposalTrash.tsx` | 프로젝트 복원·영구삭제 화면 |
