# AI비드 서비스 소개 영상

2026-10-12: `/mainPage#product-demo`에 90초 / 10개 장면 / Full HD MP4를 연결했습니다.
로그인 전후 같은 첫 화면에서 볼 수 있고, 로그인 후 업무공간 상단에도 **서비스 시연** 링크가 있습니다.
재생·일시정지·전체화면·구간 선택·한국어 자막·글로 된 소개·영상 다운로드를 지원합니다.
자동재생하지 않으며 `preload="none"`으로 방문만으로 영상 전체를 받지 않습니다.

## 발화와 손짓 동기화 — 2026-10-19 최신

실제 내레이션 구간에 맞춰 손짓을 시작하고 문장이 끝나면 중립 자세로 돌아온다.
장면 사이에는 작은 호흡을 유지한다. 검수된 얼굴 트랙은1프레임(40ms) 늦춰
음성과 맞췄으며 네 표본 구간의 CPU SyncNet 진단은 보정 전 -1, 보정 후0프레임이다.
이는 발음별 입모양 정확도나 완전한 사람 수준 자연스러움의 보장이 아니다.
화면·음성·배경을 각각 보존하고 해시로 확인하므로 이후 UI 영상만 바꿔 재합성할 수 있다.
세부 입력·검사 범위·재현 스크립트는 [제작 자료](PRESENTER_ASSETS.md)에 기록한다.

## 고정 구도와 차분한 손짓 — 2026-10-19

얼굴이 커졌다 작아지거나 좌우로 크게 움직이는 문제를 줄이기 위해 원본 머리·목·어깨를
고정한다. 아래 팔과 손만 작은 설명 동작을 이어 사용하며 입모양과 깜빡임을 유지한다.
긴 몸 영상의 누적 변형이 확인되어 이전13개 구간 연결 방식은 현재 사용하지 않는다.
검수된 두 짧은 손짓을 차분히 재사용하는 방식이며 고유한90초 전체 동작 생성이 아니다.
새 얼굴 렌더 기본값은 `steady`이며 검증된 고정 상단 몸 트랙을 요구한다.
배경은 사용자가 선택한4번 밝은 오피스를 사용한다. 한국어 F2 음성·시연 내용은 유지한다.
제작/검증 범위와 이전 버전 기록은
[제작 자료](PRESENTER_ASSETS.md)에 구분한다.

## 이전 연속 동작과 기준 얼굴 — 2026-10-19 후속

첨부 얼굴을 참고한 합성 아바타가 서서 배꼽 부근까지 보이며 설명합니다.
긴 정지 자세를 제거하고 이전17프레임의 움직임을 이어 생성하며, 중첩 구간은
모션 보정으로 연결합니다. 기준 얼굴의 외형은 재사용하고 과한 입 움직임과 무음
구간의 입 움직임을 줄입니다.2640×1080/25fps 구성으로 손끝과 아바타 프레임을
유지합니다. 우측에는 인물과 청록·네이비 뉴스 스튜디오 배경만 표시하고
이름표·소개 문구·장식 패널을 넣지 않습니다. 한국어 음성은 별도 로컬
CPU Supertonic2/F2로 제작하며, 아바타를 꺼도 같은 음성이 유지됩니다.
실제 모델·원본·파생 이미지와 생성 프롬프트는 [제작 자료](PRESENTER_ASSETS.md)에
기록합니다. 아래 Alex 항목은 이전 버전의 제작·검증 기록입니다.

배경만 바꿀 때는 얼굴/손짓/음성을 재생성하지 않습니다. 최신 무음 아바타에
`background_presenter.py`를 CPU로 적용한 뒤 기존 합성/검사를 실행합니다.
배경판 원본과 해시는 별도로 관리하며 원래 실내 배경 영상도 보존합니다.

## 이전 Alex 안내 — 2026-10-19

기존 1920×1080 시연 화면의 오른쪽에 Speak의 원본 가상 캐릭터 Alex를 배치한
2560×1080 버전을 추가합니다. 설명 음성·음악·자막·90초/10개 장면은 그대로이며,
미리 생성한 얼굴 발화 영상과 합성해 **한 비디오·한 오디오 트랙**으로 재생합니다.
구간 이동·일시정지·전체화면에 별도의 아바타 시계를 두지 않습니다.
`Alex 안내 켜짐/꺼짐`으로 원래 영상과 전환할 수 있고, 아바타 영상 오류 시 원래
영상으로 돌아갑니다. 원본 영상 해시나 스토리보드 버전·전체 길이가 달라지면
오래된 안내 버전을 선택하지 않습니다.

Alex는 직접 생성했던 성인 가상 인물이며 원본 인물 사진·학습자 음성을 사용하지
않습니다. 기존 한국어 Windows 합성 음성을 그대로 분석합니다. 입·얼굴 움직임은
Ditto/HuBERT 및 기존 LivePortrait 렌더러로 로컬에서 사전 생성합니다. 어깨는 정지
상태이며 손짓·실시간 대화·한국어 발음 정확성 검증 완료를 뜻하지 않습니다.
OpenAI/Gemma 호출, 새 모델 다운로드·설치, Speak의 소스·설정 변경은 필요 없습니다.
이 시연 작업이 전체 모델 체인의 상업적 이용 허가를 확정하는 것은 아닙니다.

| 파일 | 역할 |
| --- | --- |
| `scripts/product-demo/presenter.py` | 기존 내레이션 분석·검증된 로컬 런타임으로 얼굴 발화 영상 생성 |
| `scripts/product-demo/compose_presenter.py` | 원래 화면과 아바타를 오른쪽에 합성, 기존 음성 트랙 그대로 복사 |
| `scripts/product-demo/check_presenter.py` | 전체 프레임 디코딩·원래 음성 동일성·출처 해시·트랙 수 검사 |
| `web/public/product-demo/presenter.json` | 공개 출력의 버전·출처 SHA·제한 사항 |
| `web/public/product-demo/intro-with-guide.mp4` | 아바타 안내가 포함된 웹/다운로드 영상 |
| `.local/product-demo/presenter/` | 비공개 분석 특징·얼굴 움직임·무음 아바타 트랙·검수 자료 |

### 다시 제작하기

`$avatarResearchRoot`는 기존 Speak 아바타 연구 폴더이며 저장소에 모델 가중치나
그 환경을 복사하지 않습니다. 실제 경로는 해당 노트북에서 지정합니다.
다음은 이미 준비된 CPU ONNX 런타임과 별도 Torch CUDA 런타임을 사용하는 명령입니다.
새 설치를 자동으로 하지 않습니다. GPU 물리 여유 12GiB 미만이면 생성은 중단하고
다른 프로젝트의 모델을 내리지 않습니다.

```powershell
# 내레이션이나 장면 시간 변경 시: 이전 .local/product-demo/presenter 폴더를
# 별도 이름으로 보존한 뒤 새 작업 폴더에서 한 번만 준비합니다.
& $cpuOnnxPython -I scripts/product-demo/presenter.py prepare --research-root $avatarResearchRoot
& $avatarPython -I scripts/product-demo/presenter.py render --preview --research-root $avatarResearchRoot
.\server\venv\Scripts\python.exe scripts/product-demo/compose_presenter.py --preview
# 첫 장면을 검수한 다음 전체 얼굴 트랙을 출력합니다. 예측 움직임 캐시를 재사용합니다.
& $avatarPython -I scripts/product-demo/presenter.py render --research-root $avatarResearchRoot
.\server\venv\Scripts\python.exe scripts/product-demo/compose_presenter.py
.\server\venv\Scripts\python.exe scripts/product-demo/check_presenter.py
```

**화면 디자인만 변경**하고 음성과 장면 시간이 같다면 기존 무음 아바타 트랙을
재사용해 `compose_presenter.py`만 다시 실행합니다. **멘트·음성·시간을 변경**하면
변경된 음성과 정확히 대응하는 분석·얼굴 트랙을 다시 준비합니다. 이전 특징이나
결과를 조용히 덮어쓰지 않으며, 음성·시간 불일치는 합성 전에 차단합니다.

2026-10-19 확인: 전체 2,160프레임 디코딩, 원본/합성본의 48kHz stereo PCM
SHA 일치, 오디오 트랙 1개, 원본 영상 SHA 보존, fast-start, 자막 보존,
ESLint·TypeScript·production build를 통과했습니다. 실제 공개 HTTPS에서
90초/2560×1080 재생, 장면 선택, 재생 중 원래 영상 전환, 일시정지와 양방향
전환 시 동일 위치 유지(측정 차이 0초), 자동재생 안 함, byte-range 206을 확인했습니다.
현재 909px 화면의 가로 넘침이 없고, 428px 화면도 시각 확인했습니다. 회사 자료 API는
비로그인 시 계속 401입니다. 생성된 6개 시점 얼굴 프레임과 첫 합성 장면을
시각 검수했으며, 한국어 입 모양의 정확성과 음성·표정 자연스러움의 최종 청취
판단은 사용자 검토가 필요합니다. 실제 검수 기록/캡처는 비공개
`.local/product-demo/presenter/verification.json`, `browser-verification.json`,
`browser-preview.png`에 보존합니다.

## 구성과 참고

- 공고 검색 → 요구사항별 작성 계획 → 양식 선택 → 원문 대조 → 기존 PPTX 이어 만들기 → 참고자료 → Gemma와 페이지 수정 → 버전 보관·다운로드.
- [심비즈 안전관리](https://www.simbizkorea.com/ko/safety), [심비즈 빌더](https://www.simbizkorea.com/ko/builder)를 직접 열어 영상의 큰 제목, 장면 구분, 설명과 기능 화면을 함께 보여주는 구성을 참고했습니다. 해당 사이트의 영상·음악·로고는 사용하지 않았습니다.
- 화면은 현재 BID3의 실제 컴포넌트로 표시한 공공 공고와 별도 가상 계정의 검증 자료입니다. 일반 사용자 파일·회사 자료·인증 정보는 사용하지 않습니다. 과거 공고는 시연 사례이며 현재 모집 공고라는 뜻이 아닙니다.
- 보존 페이지, 추가 페이지, 대화, 수정·복원 이력은 기존 격리된 Gemma4 MVP 검증 자료의 복사본입니다. 촬영 계정과 복사본만 따로 준비하고 원래 자료는 변경하지 않았습니다. 촬영 후 계정은 비활성화하고 토큰을 폐기합니다.
- 작업 시간은 편집했으며 실시간 AI 실행 녹화나 성능 측정 영상이 아닙니다. 실제 생성 시간·성공률·입찰 제출 가능성을 보장하는 표현을 넣지 않습니다.
- 한국어 안내는 Windows 한국어 음성으로 로컬 합성합니다. 음악은 렌더러에서 직접 합성한 짧은 피아노 음형이며 외부 음원이나 유료 API를 사용하지 않습니다.

## 수정할 파일

| 파일 | 역할 |
| --- | --- |
| `web/features/product-demo/storyboard.json` | 장면 순서, 길이, 제목, 설명, 내레이션, 캡처 파일, 확대 범위, 강조 위치 |
| `web/public/product-demo/screens/*.jpg` | 교체 가능한 실제 화면 캡처 |
| `scripts/product-demo/render.py` | 공통 디자인, 화면 확대, 포커스, 전환, 음악, MP4·포스터·자막 출력 |
| `scripts/product-demo/narrate.ps1` | 장면별 한국어 음성 생성 |
| `web/features/product-demo/ProductDemo.tsx` | 첫 화면의 플레이어, 구간 선택, 소개 글 |
| `web/public/product-demo/build.json` | 영상과 소스 화면·스토리보드의 해시 및 출력 정보 |

웹의 구간 선택·시간·글로 된 소개와 영상·음성·자막은 **같은 스토리보드**를 사용합니다.
웹 UI 변경이 기존 영상의 픽셀에 자동 반영되지는 않습니다. 바뀐 장면의 캡처만 새로 찍고 아래 명령으로 다시 제작하면 됩니다. 전체 영상을 수동으로 처음부터 편집할 필요는 없습니다.

## UI 변경 후 업데이트

1. 바뀐 웹을 먼저 빌드하고 확인합니다. 가상 자료만 담긴 별도 계정으로 해당 화면을 엽니다. 사용자 계정의 실제 자료는 촬영하지 않습니다.
2. 현재 사용 중인 브라우저 또는 Codex 브라우저 도구로 필요한 장면을 캡처해 `screens`의 해당 JPG를 교체합니다. 데스크톱 편집 화면은 1440px 레이아웃에서 확인했습니다. 화면 크기가 바뀌면 `crop`도 확인하세요. `crop`은 원본 JPG의 `[x, y, 너비, 높이]`, `focus`는 잘라낸 화면에 대한 0~1 상대 좌표입니다.
3. `storyboard.json`의 `version`과 `capturedAt`을 바꾸고 변경된 기능 설명·내레이션도 고칩니다. 실제로 제공하지 않는 동작을 연출하지 않습니다.
4. 처음 사용할 때 영상 제작용 의존성만 설치합니다. 웹·API 실행에 추가 의존성을 넣지 않습니다.

```powershell
.\server\venv\Scripts\python.exe -m pip install -r .\scripts\product-demo\requirements.txt
```

5. 정지 장면을 먼저 확인합니다.

```powershell
powershell -NoProfile -File .\scripts\Build-ProductDemo.ps1 -Preview
```

`.local/product-demo/render/contact-sheet.jpg`와 각 장면 JPG를 열어 글자, 화면 잘림, 개인정보 노출 여부를 확인합니다.

6. 완성 영상을 다시 만듭니다. 한국어 음성·MP4·포스터·VTT 자막을 함께 출력한 뒤 전체 디코딩 검사까지 수행합니다.

```powershell
powershell -NoProfile -File .\scripts\Build-ProductDemo.ps1
```

Windows 한국어 음성이 없으면 설치하거나 `-Silent`로 음성 없이 제작할 수 있습니다. 다른 Python 환경은 `-Python '실행파일 경로'`로 지정합니다. 한국어 폰트 경로는 `BID_DEMO_FONT`, `BID_DEMO_FONT_BOLD`로 지정하며 기본은 Windows 맑은 고딕입니다. OS 글꼴 파일은 저장소에 복사하지 않습니다.

내레이션이 장면 시간보다 길면 렌더러가 실패합니다. 음성을 강제로 빠르게 재생하거나 잘라내지 말고 문장을 줄이거나 해당 장면 시간을 늘립니다.

7. `web`에서 `npm run lint`, `npx tsc --noEmit`, `npm run build` 후 웹 프로세스를 다시 실행합니다. 이미지 정적 import의 해시와 영상 URL의 버전으로 갱신됩니다.
8. 첫 화면에서 재생·구간 이동·전체화면·자막·모바일 표시·다운로드를 확인합니다. 촬영 계정을 비활성화하고 토큰을 폐기합니다.

소스만 변경하고 영상을 다시 만들지 않은 경우 다음 검사에서 실패합니다.

```powershell
.\server\venv\Scripts\python.exe .\scripts\product-demo\check.py
```

## 검증 범위

코드 검사는 프런트엔드 lint·TypeScript·production build, 영상 검사는 90초 전체 영상/음성 디코딩, 소스 해시 일치, fast-start MP4, 구간/자막 개수 일치를 포함합니다.
브라우저에서는 실제 HTTPS 재생, 자막 로딩, 구간 선택, 처음부터 재생, 전체화면, 다운로드 및 모바일 390px 화면을 별도로 확인합니다.
화면 캡처 갱신과 내레이션 문장 검수는 사람이 실제 서비스와 비교하는 단계로 남습니다.

2026-10-12 검증 결과: 위의 전체 제작 명령, 전체 디코딩 검사, lint·TypeScript·production build를 통과했습니다. 실제 HTTPS에서 구간 이동, 한국어 자막, 전체화면, 소개 글, 다운로드 파일의 SHA-256 일치와 390px 모바일 표시를 확인했습니다. 영상 요청은 byte range에 206으로 응답합니다. 첫 방문에는 자동재생하지 않습니다. 촬영 계정은 로그아웃 후 비활성화했고 인증 토큰을 폐기했으며, 촬영용 복사본은 보관 처리했습니다.

2026-10-15 갱신: 빈 촬영 계정으로 분야별 템플릿 장면을 다시 촬영하고 안내 음성·자막과 90초 영상을 재제작했습니다. 버전은 `20261015-1`입니다. 해당 장면만 최신 촬영일을 기록하고 나머지 장면은 기존 촬영본을 유지했습니다. 전체 영상·음성 디코딩, 소스 해시·자막·fast-start 검사와 웹 production build를 통과했습니다. 실제 사용자 회사 문서나 제안서를 공개 영상에 넣지 않았습니다.
