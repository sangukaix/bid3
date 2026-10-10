# Bid2 문서 안내

집 컴퓨터에서 작업을 다시 시작할 때 이 문서부터 읽습니다.

2026-10-10 현재 MVP 구현·검증 상태는 [제안서 검증 기록](PROPOSAL_QUALITY_VALIDATION.md), 일반 발표자료 기능은 [발표자료 작업실](PRESENTATION_STUDIO.md), 로컬 Gemma 설정은 [LLM 설정](LLM_SETUP.md)을 먼저 확인합니다. 아래 8월 인계 문서는 과거 구조·계획 설명이며 최신 동작의 기준이 아닙니다.

## 읽는 순서

1. `SETUP_NEW_PC.md` - 새 Windows 컴퓨터에 개발환경 설치
2. `RESUME_PROMPT.md` - 새 Codex 작업창에 보낼 첫 메시지
3. `HANDOFF.md` - 2026-08-22 현재 완료 상태와 바로 다음 작업
4. `MAPPING.md` - 폴더, 파일, 데이터 이동 흐름
5. `TODO.md` - 앞으로 진행할 작업 순서

## 참고 문서

- `PROPOSAL_REFERENCE_GUIDE.md`: 좋은 제안서의 구성과 Bid2 적용 원칙
- `BID2_과제_설계_문서.md`: 수업 과제 제출용 아키텍처·Prompt·RAG 설명

## 기준

- 현재 동작과 검증 범위는 위 최신 검증 문서를 기준으로 하며, `HANDOFF.md`는 과거 인계 기록입니다.
- 기능 위치를 찾을 때는 `MAPPING.md`를 봅니다.
- 다음 개발 작업을 고를 때는 `TODO.md`를 봅니다.
- `.env`, `db.sqlite3`, `media`, `chroma_db`, `venv`, `node_modules`는 Git에 포함되지 않습니다.
