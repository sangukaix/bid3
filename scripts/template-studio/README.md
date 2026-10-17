# 분야별 제안서 양식

분야 6개와 각 분야의 기본 디자인 변형 2개, 교육 사진형 양식 1개를 관리합니다. 내용과 페이지 구성은 `domain-profiles.mjs`, 편집 가능한 PPTX 작성은 `build-domain-templates.mjs`에 있습니다. 기존 스튜디오 양식 30개는 유지합니다.

| 분야 | 주요 구조 |
| --- | --- |
| 교육·연수 | 과정 매트릭스, 학습 흐름, 출석·평가, 연차별 운영 |
| 공사·시설 | 공종 WBS, 개념 공정표, 품질 승인점, 안전, 준공 인계 |
| IT·시스템 | 현행·목표, 계층별 구성, 요구사항 추적, 전환·시험·개통 |
| 조사·연구·컨설팅 | 연구 질문, 조사 설계, 자료 검증, 정책 대안 |
| 행사·홍보 | 콘셉트, 운영 큐시트, 기능 구역, 참가자 여정, 비상 대응 |
| 물품·설비 납품 | 품목 체계, 규격 대응, 제조·공급 이력, 설치·검수·보증 |

본문 구성은 분야마다 다르고 같은 분야의 두 변형은 구성은 공유하면서 표지 위치, 헤더 구분선, 색을 달리합니다. 표·도식·텍스트는 PowerPoint 개체입니다. 설명용 사진은 수행 증빙이 아닙니다. 이미지 원문은 `server/proposal_templates/domain_assets/sources.json`, 조사 원문 목록은 `server/proposal_templates/domain_sources.json`에 있습니다.

재생성 시 Codex 번들 Node/Python과 `@oai/artifact-tool`을 사용합니다. 환경변수 `RUNTIME_NODE_MODULES`, `RUNTIME_PYTHON`, `PRESENTATIONS_SKILL_DIR`에 설치 경로를 지정합니다. `OUTPUT_DIR`은 `.local/theme-studio-20261014/` 아래 새 폴더명으로 지정하고, 필요하면 `ONLY_DOMAIN`으로 한 분야를 선택합니다. 작성 스크립트는 OpenAI 또는 Ollama를 호출하지 않습니다.

1. `build-domain-templates.mjs`로 12개 빈 양식과 6개 작성 샘플을 생성합니다.
2. 프로젝트 Python으로 `render-domain-templates.py`를 실행해 설치된 PowerPoint에서 PDF와 페이지 PNG를 만듭니다.
3. 모든 페이지를 확인한 뒤 `publish-domain-templates.py`로 검토본과 라이브러리를 갱신합니다. 이미지 미리보기는 PPTX SHA-256과 장수가 일치해야 사용됩니다.
4. 실행 중인 Django를 다시 시작해 새 카탈로그를 읽게 합니다. 분야별 선택·미리보기·다운로드와 생성 후 구조 보존을 검증합니다.

원문 다운로드 자료는 `.local/theme-studio-20261014/references/`에, 이번에 확인한 최종 샘플과 다운로드 묶음은 `.local/theme-studio-20261014/review/`에 있습니다. 교육 샘플은 기존 KOTRA 공고의 검토용이며 나머지 5개 샘플은 가상 과업입니다. 실제 제출 시 해당 공고의 필수 목차·분량·서식과 현행 회사 증빙을 우선합니다.

회사 자료의 시각 요소는 `layouts.json`의 `material_slot`에만 배치합니다. 나머지 공정표·WBS·시스템 구성·규격표의 본문 구조는 유지하고, 회사 텍스트는 기존 근거 검토 절차로 현재 과업에 맞게 작성합니다.

## 교육 사진형 양식

교육 분야의 기본 추천은 `education_photo`(21쪽)입니다. `build-photo-template.mjs --source <승인된 사진형 PPTX> --work <비공개 작업 폴더> --mode template`로 작성합니다. `actual` 모드는 같은 디자인의 해당 공고 검토본을 만들며 공용 라이브러리에 설치하지 않습니다. 회사 업로드 이미지·화면과 특정 공고명·연도·금액은 공용 양식에서 제거하고, 회사 자료는 생성 시 소유자의 자료만 지정 영역에 배치합니다. 특정 공고의 예산 차트도 재사용하지 않습니다.

패키지·레이아웃·재가져오기 검증 후 PowerPoint로 PDF와 페이지 PNG를 출력해 전부 확인합니다. `publish-photo-template.py --work <작업 폴더>`로 공용 PPTX, 21쪽 미리보기와 SHA manifest를 함께 설치합니다. 새 버전의 파일명은 `--deck <확정 PPTX> --receipt <검증 receipt JSON>`으로 지정할 수 있습니다. 미리보기는 같은 출력의 `render-template/01.png`부터 `21.png`까지 준비합니다. 내부 검수표는 별도 PDF로 내보내며 제안서에 검수용 장문 페이지를 자동 추가하지 않습니다.
