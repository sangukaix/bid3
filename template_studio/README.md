# BID3 제안서 템플릿 스튜디오

앱 로직과 분리한 양식 제작 소스입니다. `catalog.mjs`에서 디자인·분류·20쪽 구성을 관리하고, `build.mjs`에서 편집 가능한 PPTX를 만듭니다.

## 구성

- 신규 30종: 공공·행정, 교육·연구, 기술·디지털, 환경·시설, 경영·컨설팅, 문화·홍보 각 5종
- 각 20쪽, 16:9, 한국어 글꼴 `Malgun Gothic`
- 본문과 표는 PowerPoint의 실제 텍스트·표 객체
- 표지용 이미지 3종은 이번 작업에서 별도로 생성한 원본이며 배경으로만 사용
- 외부 사이트의 템플릿·이미지·로고·스크린샷은 배포 파일에 포함하지 않음
- 공고의 수치, 실적, 일정은 기본값으로 만들어 넣지 않음. 비어 있는 업무 정보는 확인 필요로 표시

배포 위치: `server/proposal_templates/library/`. 앱 실행에는 제작용 도구나 외부 사이트 계정이 필요하지 않습니다. 기존 5종은 유지합니다.

## 앱에서 사용

로그인 후 왼쪽 **PPT 양식 → 디자인 템플릿 선택하기**에서 35종을 검색하거나 용도별로 볼 수 있습니다. 원하는 양식을 누르면 20쪽 전체를 확인하고 원본 PPTX를 다운로드할 수 있습니다.

**이 템플릿 선택**을 누르면 이 브라우저의 새 제안서 기본 양식으로 저장됩니다. 이미 작성한 제안서의 양식은 바뀌지 않으며, 공고별 제안서 제작 화면에서도 다시 선택할 수 있습니다. 양식 선택·다운로드에는 LLM이 필요 없고, 내용 작성에는 유지보수 화면에서 설정한 모델을 사용합니다.

## 재생성

Codex의 제공 런타임과 프레젠테이션 도구가 있는 Windows 환경에서:

```powershell
powershell -NoProfile -File template_studio/Build-Library.ps1 -Revision my-new-design
server/venv/Scripts/python.exe template_studio/render_library.py --revision my-new-design
```

`Revision`은 새 이름을 사용합니다. 검증 보고서와 작업 PDF는 `.local/template-studio`에 남습니다. 최종 파일을 설치하기 전에 `render_library.py`가 실제 PowerPoint로 변환하고 각 페이지의 텍스트 누락을 검사합니다. 디자인 변경 후에는 렌더된 페이지도 확인해야 합니다.

한 종류만 수정할 때는 제작 명령에 `-TemplateId civic_navy`, 변환 명령에 `--template-id civic_navy`를 추가합니다. 변환 명령은 `--template-id`를 여러 번 지정할 수 있습니다.

미리보기는 원본 PPTX의 SHA-256과 연결됩니다. PPTX만 교체하면 기존 이미지가 그대로 노출되지 않고 서버의 변환 경로로 돌아갑니다. 양식 변경 시 PPTX·미리보기·catalog·layouts를 함께 갱신하세요.

## 참고 조사

2026-09-25에 사용자가 제공한 네 사이트를 확인했습니다. 이 라이브러리는 원본 다운로드 30종이나 동일 복제본이 아니라 BID3에서 사용·수정할 수 있도록 별도 제작한 30종입니다.

| 사이트 | 확인한 내용 | 이번 적용 |
|---|---|---|
| [Oreate](https://www.oreateai.com/home/vertical/htmlPPT/ko) | 추천 양식 갤러리, Q3 마케팅 전략 보고서 상세 미리보기. 네이비·친환경·미니멀·그라데이션 표지 등 | 대비, 여백, 제목 위치의 참고. 원본 미포함 |
| [미리캔버스](https://www.miricanvas.com/ko/template/presentation) | 전통 제안, 사업화 기획, 민트 기업 보고, 그린 포트폴리오, 넘버링 발표 등 공개 갤러리 | 용도별 분류와 국내 보고서의 읽기 순서 참고. 원본 미포함 |
| [Gamma](https://gamma.app/ko/templates/client-proposal-b8d42gtyh2kn4qs) | 고객 제안 상세, 회사·연구·교육·일정 등 템플릿 목록 | 고객 문제→접근 방법→일정·팀→근거 흐름 참고. 원본 미포함 |
| [Genspark](https://www.genspark.ai/ai_slides?tab=skills) | 공공 정책 6종 갤러리, 정책 브리핑 상세 및 다운로드 형식 | 다운로드는 HTML·PNG·지침 ZIP임을 확인. 원본 및 지침 코드는 배포·실행하지 않음 |

외부 서비스의 로그인·회원가입·결제는 수행하지 않았습니다. 공개 갤러리와 다운로드로 조사했습니다.

### 이용 조건 확인

- [미리캔버스 라이선스](https://help.miricanvas.com/hc/en-us/articles/10454608583961-MiriCanvas-License-Agreements-Effective-Date-October-13-2022): 무료 공급자 콘텐츠와 일반/유료 콘텐츠를 구분하며, 다른 편집 프로그램에서 재편집 가능한 양식의 배포에 제한이 있습니다. 개별 요소별 허용 여부를 확인하지 않은 원본을 라이브러리에 넣지 않았습니다.
- [Gamma 약관](https://gamma.app/terms): 사용자가 만든 콘텐츠와 Gamma의 테마·서비스 자산의 권리는 별개입니다. 외부 템플릿 라이브러리 배포 허용을 확인하지 못했습니다.
- [Genspark 약관](https://www.genspark.ai/ko/terms): Genspark 콘텐츠의 외부 이용·배포에 제한이 명시되어 있습니다. 공개 다운로드 파일에도 별도 재배포 라이선스가 없었습니다.
- [Oreate 약관](https://www.oreateai.com/protocol/termsConditions): 약관 페이지의 본문을 조회 도구에서 확인하지 못했으므로 외부 재배포 허용으로 추정하지 않았습니다.

## 표지 이미지 제작 기록

내장 이미지 생성 도구로 새로 생성했습니다. BID3의 OpenAI API 키·크레딧을 사용한 기능이 아니며, 앱에서 선택·생성할 때 이미지 API를 호출하지 않습니다.

- `assets/navy-glass.png`: 16:9, 짙은 네이비 건축적 면과 오른쪽의 푸른 유리 곡면, 왼쪽 65% 제목 여백, 텍스트·로고 없음
- `assets/sage-paper.png`: 16:9, 아이보리 수제 종이와 오른쪽 세이지 잎 그림자, 밝은 왼쪽 제목 여백, 텍스트·로고 없음
- `assets/plum-silk.png`: 16:9, 왼쪽 자두·로즈·살구색 실크 주름과 오른쪽 옅은 라벤더 여백, 텍스트·로고 없음

원래 프롬프트의 목적은 모두 `original premium presentation background`이며 외부 양식 이미지의 편집·복제가 아닙니다.
