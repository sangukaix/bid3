# 서 있는 안내 아바타 제작 자료 — 2026-10-19

## 뉴스 스튜디오 배경 — 2026-10-19 최신

사용자 요청에 따라 밝은 식물/목재 실내를 청록·네이비 뉴스 스튜디오로 교체한다.
현재 인물의 외형·손짓·얼굴 발화·한국어 F2 음성·90초 시계는 그대로 재사용한다.
이 절의 배경 교체는 아래 연속 동작/얼굴 생성이 끝난 뒤 적용하는 별도 단계다.

- 배경판: `web/public/product-demo/presenter/newsroom-studio.png`.
  built-in `image_gen`으로 생성한 빈 스튜디오이며 외부 방송사 로고/화면을 복사하지
  않았다. 실제 촬영 장소나 실제 방송 출연 영상이 아니다. 정확한 최종 프롬프트는
  [presenter-newsroom-prompt.txt](presenter-newsroom-prompt.txt)에 보존한다.
  프로젝트 OpenAI API 키를 사용하지 않지만, 배경판은 로컬 LLM 생성물이 아니다.
- 인물 분리: [공식 Robust Video Matting](https://github.com/PeterL1n/RobustVideoMatting)의
  `v1.0.0/rvm_mobilenetv3_fp32.torchscript` (15,501,891 bytes), SHA256
  `f01e0c9338b9a6a31b881ea6d4360d70c1e549701b3792e14c9ed88d6196c5a1`.
  GPL-3.0 라이선스 모델을 비공개 오프라인 제작 단계에서만 사용하며 앱 의존성이나
  배포 소스/공개 폴더에 모델·원본 코드를 넣지 않는다.
- `background_presenter.py`: TorchScript CPU 4스레드, downsample ratio0.5.
  공식 [추론 설명](https://github.com/PeterL1n/RobustVideoMatting/blob/master/documentation/inference.md)에
  맞춰 전체 영상에서 네 recurrent state를 이어 사용한다. 프레임마다 상태를 초기화하지
  않는다. 불투명 인물 내부(alpha≥0.995)는 기존 RGB를 유지하고 경계부는 모델의
  foreground/alpha로 기존 밝은 실내 색 번짐을 줄인다. 추가 얼굴 생성·색 보정은 없다.
- GPU를 쓰지 않고 다른 작업의 Gemma/서버/모델 설정을 변경하지 않는다.
  512×768/25fps 아바타의 프레임 수와 시간, 손·팔·머리 위치를 유지한다.
  최종 합성에서는 기존처럼720×1080으로 비율 확대한다.
- 기존 입력: `.local/product-demo/presenter-natural-v4-20261019/avatar.mp4`.
  새 출력: `.local/product-demo/presenter-newsroom-20261019/avatar.mp4`.
  `inputs.json`은 그대로 복사하고 `render.json.background`에 원본 영상·배경판·모델 해시,
  실제 처리 시간과 검토 표본을 기록한다. 기존 공개 영상은 새 작업 폴더의
  `previous-public/`에 보존한다. 원래 등록 얼굴과 포즈 이미지의 실내는 수정하지 않는다.
- 배경판만 바꾸려면 기존 원본 아바타에 다시 적용한다. 이전에 합성한 뉴스 배경 영상에
  연속 재적용하지 않는다. 화면 디자인 변경은 기존 `compose_presenter.py`로 다시
  합성하며, `check_presenter.py`가 배경판/영상/자막/음성 해시를 확인한다.

재현 명령(격리된 기존 제작용 `$bodyPython` 사용):

```powershell
& $bodyPython -I scripts/product-demo/background_presenter.py --source-work .local/product-demo/presenter-natural-v4-20261019 --work-dir .local/product-demo/presenter-newsroom-20261019 --background web/public/product-demo/presenter/newsroom-studio.png --checkpoint .local/product-demo/presenter-newsroom-20261019/models/rvm_mobilenetv3_fp32.torchscript
.\server\venv\Scripts\python.exe scripts/product-demo/compose_presenter.py --work-dir .local/product-demo/presenter-newsroom-20261019
.\server\venv\Scripts\python.exe scripts/product-demo/check_presenter.py --work-dir .local/product-demo/presenter-newsroom-20261019
```

머리카락·움직이는 손 가장자리의 미세한 알파 오차는 모델 합성의 한계다.
디코딩/해시 검사가 모든 프레임의 시각적 완전성이나 실제 인물의 발화임을 보장하지 않는다.

이번 결과: 버전 `1a7ed209aac3`, 2640×1080/25fps/90초, 22,421,605 bytes.
CPU 배경 분리/합성은217.890초였으며 비교 성능 실험은 아니다. 인물 영상 표본은
0·150·500·1000·1250·1500·2000·2249프레임을 시각 확인했다.
전체2250프레임 디코딩, 단일 음성, 화면 전용/합성본의 디코딩 음성 SHA 일치,
배경판/포스터/자막/시연 원본 해시, fast-start 검사를 통과했다. production build와
TypeScript 검사를 통과했다. 실제 HTTPS에서 새 버전2640×1080 재생을 확인했고,
영상 range206, 공개 포스터 SHA 일치, 미로그인 회사 자료 API401을 확인했다.
원본 얼굴 모델/동작은 바꾸지 않았으며 해당 생성 모델을 다시 실행하지 않았다.
일반 브라우저에서0초부터90초 종료까지 재생했고 media error는 없었다.
검수 중 정지 상태의 소스 전환에서 이전 자막이 겹쳐 남는 현상을 발견해
`ProductDemo.tsx`의 비디오를 소스별 key로 새로 등록한다. 기존 pending seek와
재생 복원 동작을 유지한다. 수정 후 정지 전환은15.799634초로 양방향 유지했고,
재생 중 전환도 계속 재생됐다. 최종53.569초 부근에서 중복 없는 자막 한 줄,
새 배경, 자막 readyState2,609px 뷰포트의 가로 넘침 없음을 확인했다.
실제 화면과 기록은 새 작업 폴더의 `browser-preview.png`,
`browser-verification.json`, `http-verification.json`, `verification.json`에 보존한다.

## 연속 동작·자연스러운 얼굴 보정 — 2026-10-19 후속

사용자가 지적한 몸 동작 정지와 얼굴/입의 부자연스러움을 별도로 수정한다.
이 절은 최신 변경이고, 아래의 다섯 손짓/고정 자세 기록은 f77d566 이전 출력의 기록이다.

- 기존 몸: 두7.72초 손짓을 다섯 번 배치하고 나머지51.4초는 마지막 몸 프레임 유지.
  새 몸: 앞 구간의 마지막17프레임을 다음 LTX 생성의 영상 조건으로 전달한다.
  중첩17프레임을 제외하고 새 프레임만 연결하며, 영상 전체를 채우기 전에는
  연속 동작 출력으로 합성할 수 없다. 동일 클립 반복이나 정지 프레임 삽입은 하지 않는다.
- 긴 출력의 원시 연결부 검사에서 후반 세 곳에 자세/선명도 점프가 발견됐다.
  `stitch_body.py`는 겹치는17프레임에서 앞 영상과 재구성된 영상의 optical flow를
  맞춘 뒤 smoothstep으로 연결한다. 원시 생성물은 그대로 보존한다. 순수한 한 번의
  모델 생성이90초 내내 완벽히 연속이라는 뜻으로 설명하지 않는다.
  겹친 뒤2046프레임의 몸 동작만2250프레임으로 모션 보간해 약0.9093배의 차분한
  속도로 맞춘다. 음성·발화 시계는90초 그대로이고, 프레임 유지/손짓 루프를 쓰지 않는다.
  최종2250프레임은 원시 생성과 모션 보간을 포함하며 모두 순수 모델 출력이라고
  설명하지 않는다. 부드러운 연결이 손가락/얼굴의 완전한 자연스러움을 뜻하지 않는다.
  단순 모션 합성에서 일부 손이 반투명하게 겹쳐 보여 그 후보는 채택하지 않았다.
  최종 연결은 두 워프 영상의 차이가 큰 가림/손가락 영역에서 하나의 관측을 선택해
  이중 노출을 줄인다. 원시 몸/실패한 두 연결 후보/채택한 연결 후보를 각각 보존한다.
- 기존 얼굴: 매 몸 프레임에서 외형 특징을 다시 추출해 외형 변화와 흐림이 전파됐다.
  새 얼굴: 등록 원본의 appearance/기준 keypoints를 재사용하고 몸의 작은 자세 변화만
  상대적으로 반영한다. 원본 전체 얼굴을 매 프레임 다시 생성하는 방식과 구분한다.
- 입: 캐시된 음성 기반 움직임을 유지하면서 입 keypoint 변화에0.72 gain을 적용한다.
  실제 음성 WAV의 RMS로 무음 구간의 입 움직임을 줄이고, 조용한 자음 주변120ms는
  보호한다. 말 내용·음성 속도·원래 WAV는 바꾸지 않는다.
- 눈: 첫 후보의 오디오 기반 눈 제어는 과하게 눈을 떠 채택하지 않았다. 이후 몸의
  눈 변형을 섞는 후보에서도 눈 밑 번짐이 보여 원인을 조사했다. 현재는 기존 로컬
  LivePortrait 눈 전용 retargeter와 명시한 불규칙 blink clock을 사용하고, 고개는
  첫 몸 프레임을 기준으로 한 상대 변화로 처리한다. 깜빡임 시점은 학습한 대화 반응이
  아닌 제작자가 정한 애니메이션이다.2.4MB 기존 모델을 재사용하며 새 다운로드는 없다.
- 눈 밑 번짐의 주 원인은 예전 손 인사 영상의 lower-left 제외 마스크가 새 구도의
  왼쪽 눈 아래까지 적용된 것이었다. `face_blend_mask`는 새 구도에서 두 눈 주변을
  기준 얼굴100%로 유지한다. 손 인사 전용 마스크는 legacy 모드에서만 사용한다.
- 합성: 아바타의25fps를 유지하고 원래24fps 시연 화면만25fps로 맞춘다.
  화면 전용/아바타 영상은 동일 음성 트랙과 자막 시계를 유지한다.
- 효율: 이전 음성 특징10개와2250프레임 발화 motion 캐시를 검증해 재사용한다.
  연속 몸 제작은 같은 프로세스에서 동일 검증 모델·정확히 같은 프롬프트의 runtime을
  재사용한다. 다른 작업의 모델을 비우지 않으며 각 구간 전에 물리 VRAM 여유를 확인한다.

수정 파일: `scripts/product-demo/continuous_body.py`, `gesture.py`,
`stitch_body.py`, `presenter.py`, `compose_presenter.py`, `check_presenter.py`.
핵심 함수는 `load_gestures`, `speech_activity`, `restrained_expression`,
`render`다. 등록 인물·이미지·한국어 F2 음성은 기존과 같다.
몸의 새 프레임과 입 움직임은 기존 로컬 모델로 만들었고 새로운 이미지 생성이나
프로젝트 OpenAI API 호출을 하지 않는다.

비공개 작업 폴더:
`.local/product-demo/presenter-natural-20261019/body`에 연속 몸과 구간별 생성 조건,
`presenter-natural-v4-20261019`에 최종 얼굴 보정 출력을 둔다.
현재 연결 후보의 출력 폴더는 `presenter-natural-20261019/body-smooth-v3`다.
첫 과장된 눈 후보는 `presenter-natural-20261019/avatar-preview.mp4`에 보존한다.
그 후보를 현재 품질 개선의 근거로 사용하지 않는다.
눈 retargeter 모델 SHA256:
`3652d5a3f95099141a56986aaddec92fadf0a73c87a20fac9a2c07c32b28b611`,
LivePortrait 소스 revision `9b294b3d0536135442ea73cb01e6cb3ca7029dd3`.
관련 구현은[공식 eye retargeter](https://github.com/KlingAIResearch/LivePortrait/blob/9b294b3d0536135442ea73cb01e6cb3ca7029dd3/src/live_portrait_wrapper.py)를 확인했다.

14.72초 수정 후보와 이전 버전을 같은 음성으로 일반 브라우저에서 재생했다.
약12.7초의 이전 몸은 손을 모으고 있고 수정 후보는 손이 움직이는 것을 확인했다.
양쪽 모두 끝까지 디코딩됐고 media error는 없었다. 눈 과장 후보는 이 비교 전에
제외했다. `review/browser-pilot.json`, `face-comparison-v2.jpg`에 비교 자료를 보존한다.
프레임 차이/디코딩 성공은 정지 프레임 삽입 여부와 실행 검증이며, 한국어 음소 정합성
또는 자연스러움 전체를 보장하는 점수가 아니다.

다시 제작할 때는 먼저 두 구간으로 짧게 검수하고 같은 작업 폴더에서 이어간다.

```powershell
& $bodyPython -I scripts/product-demo/continuous_body.py --research-root $research --body-python $bodyPython --output "$work/body" --in-process --max-new-chunks 2
# 구간 원본/손 모양/연속성을 검수한 뒤 같은 명령에서 max-new-chunks 제한을 제거한다.
& $bodyPython -I scripts/product-demo/continuous_body.py --research-root $research --body-python $bodyPython --output "$work/body" --in-process
& $bodyPython -I scripts/product-demo/stitch_body.py --source "$work/body" --output "$work/body-smooth"
# 전체 프레임의 시각 검수와 acceptance.json을 기록한 후 생성한다.
& $avatarPython -I scripts/product-demo/presenter.py render --research-root $research --work-dir $faceWork --gesture-dir "$work/body-smooth" --face-style natural
```

## 최종 출력 검증 — 2026-10-19

선택 출력: `presenter-natural-v4-20261019/avatar.mp4`와
`presenter-natural-20261019/body-smooth-v3`다. 공개 버전은 `4db65842749d`,
2640×1080/25fps/90초, MP4는22,945,540bytes다.
전체2250프레임 디코딩, 소스·포스터·자막 해시, fast-start, 음성 트랙1개와
화면 전용/아바타 출력의 디코딩 오디오 SHA 일치를 확인했다.
원래 `intro.mp4` 해시는 그대로다. 기존 음성과 시연 내용은 유지했다.

최종 몸2250프레임의 해시는 모두 다르고 인접 몸 영역이 완전히 같은 프레임은0개다.
이는 정확한 정지/복제 프레임이 없다는 검증이며 자연스러움 점수가 아니다.
원시 몸13구간의 샘플, 최종 몸12개 시점, 손 겹침 수정 비교, 얼굴6개 시점과
첫 blink의 전/중/후를 확인했다. 원시 연결에서 큰 점프가 보였던 세 구간의
진단 차이는24.47/31.24/48.52에서 보정 후3.80/4.73/11.87로 줄었다.
값은 지정한 몸 ROI의0~255 RGB 절대차 평균이며, 실제 자연스러움/음소 정합성
또는 사람 대상 평가 지표가 아니다.

CPU 단위 검증은 얼굴/시계/캐시/배치10개와 모션 연결4개를 통과했다.
새 마스크는 두 눈 주변이 기준 얼굴100%가 되는 회귀 검증을 포함한다.
production build(TypeScript 포함)를 통과했다. 실제 공개 HTTPS에서0초 시작,
45.69초 재생 상태,90초 ended=true/mediaError=null을 확인해 일반 재생이 끝까지
진행됨을 확인했다.65초 구간 이동 후 일시정지 양방향 아바타 전환 위치 차이는0초였다.
초기 자동재생 안 함/preload=none, 자막 readyState2,609px 화면의 가로 넘침 없음,
동영상 range206, 공개 포스터 해시 일치와 비로그인 회사 API401을 확인했다.
사용자 음성/입의 정확한 음소 일치와 주관적인 실사 자연스러움 전체를 보증하지 않는다.

검수 자료는 최종 얼굴 작업 폴더의 `verification.json`, `http-verification.json`,
`browser-verification.json`, `browser-preview.png`, `final-face-contact.jpg`와
몸 작업 폴더의 `body-audit.json`, `final-body-contact.jpg`에 있다.
새 인물 원본 이미지 제작/음성 재합성/음성 특징 재분석/발화 motion 재예측은 하지 않았고,
기존 입력·특징·motion 캐시를 검증해 재사용했다. 최종 얼굴 출력은 motion cache
재사용을 실제 실행 기록으로 남긴다. 기존 모델·다른 프로젝트·공개 터널 주소는 보존했다.

## 이전 서 있는 버전의 제작 기록

최신 요청: 사용자가 첨부한 얼굴을 참고해 기상캐스터처럼 서서 배꼽 부근까지 보이며
손으로 설명한다. 한국어 여성 합성 음성과 문구 없는 실내 배경을 유지한다.
이 버전은 첨부 얼굴을 참고한 합성 장면이다. 조이 또는 앞서 만든 앉은 인물을
사용하지 않으며, 참조 인물이 실제 출연하거나 말한 녹화 영상이라는 뜻이 아니다.

## 선택본과 출처

- `web/public/product-demo/presenter/standing-neutral.png`: 중립 자세, 얼굴 발화 등록 원본.
- `web/public/product-demo/presenter/standing-explain.png`: 양손 설명의 중간 자세.
- `web/public/product-demo/presenter/standing-screen.png`: 왼쪽 시연 화면 안내의 중간 자세.
- 출처·인물·중립 자세 해시·수동 얼굴 등록 좌표:
  `web/features/product-demo/presenter-source.json`.
- 내장 `image_gen` 도구의 얼굴 유지 편집으로 제작했다. CLI/API 키 경로를
  사용하지 않았다. 원본 첨부 사진은 공개 소스에 복사하지 않고 비공개 작업 폴더의
  `user-face-reference.png`에 보존한다. 출력 원본의 SHA는 `inputs.json`,
  중간 자세는 각 동작의 `report.json`에 기록한다.
- 모든 생성·편집 프롬프트는 아래에 보존한다. 이전 앉은 후보는 비공개 작업 폴더에
  보존하고 현재 공개 아바타의 원본으로 사용하지 않는다.
- 음성은 Supertonic2 기본 F2 한국어 여성 합성 음성이다. 참조 사진 인물의 목소리를
  복제한 것이 아니다. 언어 `ko`, 속도1.13,12steps, CPU ONNX.
  공식 모델 [Supertone/supertonic-2](https://huggingface.co/Supertone/supertonic-2),
  revision `75e6727618a02f323c720cba9478152d4bc16ca4`,
  별도 환경 `supertonic==1.3.1`.
- 몸 동작은 LTX-Video2B0.9.6distilled, 얼굴 발화는 Ditto/HuBERT/렌더러로
  로컬에서 사전 생성한다. Speak의 기존 연구 런타임·범용 가중치만 읽기 전용으로
  재사용하며, Speak의 캐릭터·설정·소스를 수정하지 않는다. 다른 작업의 모델을
  강제 종료하거나 Gemma 설정을 변경하지 않는다.
- 이미지 생성은 Codex 내장 도구를 사용했다. 영상/음성 작업의 외부 추론 호출0회를
  이미지 생성까지 전부 오프라인이라는 뜻으로 설명하지 않는다.
  완성 MP4 재생에는 GPU 추론이나 Gemma가 필요하지 않다.

## 실제 이미지 프롬프트와 계보

첫 편집은 사용자 첨부 얼굴 사진을 입력으로 사용했다. 두 번째는 첫 출력의
카메라 구도를 수정했다. 양손 설명은 중립 자세에서 만들고 손을 안쪽으로 모으는
수정을 한 번 더 했다. 화면 안내 자세는 중립 자세에서 만들었다.
모든 단계는 내장 image_gen이며 선택본 세 장을 프로젝트에 저장했다.

### standing_from_user_reference

> Use case: identity-preserve.
> Asset type: reference-based synthetic presenter for a Korean service walkthrough, portrait 1024x1536.
> Input image 1 is the FACE AND HAIR identity reference supplied by the user. Preserve the recognizable adult woman's face, eye shape, nose, mouth, jawline and black shoulder-length softly waved hair. Do not replace her with a generic new face or beautify her facial structure.
> Create a new scene: she stands upright like a professional Korean weathercaster explaining a service. Eye-level locked camera, facing the viewer, entire head with breathing room through just below the navel/waist visible, both elbows and COMPLETE hands inside the frame. She wears a simple tailored midnight-navy blazer over a plain ivory blouse, fully clothed waist, polished contemporary professional styling. Her hands rest gently together at upper waist as a neutral explanatory presenter pose. Shoulders relaxed and level, head upright and looking directly at camera, slight warm closed-mouth smile.
> Background: a refined bright real studio room, warm off-white wall, restrained light wood accents and a subtle out-of-focus plant at the side. Diffused soft daylight, clean depth. No desk or chair, no screen, no other person.
> Photorealistic natural skin texture and consistent photographic light. Presenter fills the portrait frame but leave space on each side for future hand gestures below her chest. Both hands anatomically natural, no cropped fingers.
> Output ONLY the standing presenter in her room. No captions, logos, news branding, nameplate, graphic overlays, watermark, borders or interface. This is a new synthetic presenter scene, not the original newspaper photograph.

### waist_framing

> Use case: identity-preserve. Edit target: this standing synthetic Korean presenter. Preserve her exact face and hair, navy blazer, ivory blouse, warm studio room, lighting, eye contact and neutral hands gently together at waist. Change ONLY camera framing to the waist-up weathercaster framing requested: the bottom edge must end just below her complete hands at navel/waist height, with NO thighs or upper legs visible. Head and both complete hands remain visible, leave breathing room above head and to sides. Tighten the crop by moving the camera closer, not changing her anatomy. Vertical 1024x1536 composition. Only presenter and room, no text/graphics/logos.

### explanatory_pose

> Use case: identity-preserve. Edit target: the attached standing waist-up synthetic presenter. This is a middle keyframe of an explanatory gesture.
> Change ONLY her arms/hands: open both forearms slightly outward at upper-waist/lower-chest level, both palms gently facing upward as if calmly explaining two options. Hands below chest and far below chin, fingers relaxed and anatomically natural, both complete hands and elbows remain within the frame with margin. The right hand on viewer's left may extend a little farther toward the adjacent service demonstration. This is a restrained weathercaster explanation, NOT a greeting wave.
> Preserve EXACTLY her recognizable face, head position and size, black hairstyle, soft expression, eye contact, navy blazer/ivory blouse, standing posture, waist-up camera crop, background and lighting. No zoom or camera movement. Portrait 1024x1536. Only presenter and room, no writing/logos/interface.

### explanatory_pose_inset

> Use case: precise-object-edit / identity-preserve. Change ONLY the placement of both open hands and forearms of this exact standing presenter: bring each open palm inward toward the torso by about one hand-width, leaving a clear margin of at least 120 pixels between every fingertip and either side edge of the 1024px-wide image. Hands remain gently palm-up below chest, an understated explanatory gesture. Both complete hands must stay within the central 75 percent of the image width; do not spread the arms far apart. Preserve exact face, head, hair, facial expression, body position, blazer, blouse, room, lighting and camera framing. Same 1024x1536 portrait, no text or graphics.

### screen_guidance_pose

> Use case: identity-preserve. Edit target: the attached standing waist-up presenter with hands resting together.
> Change ONLY the right arm and hand (on viewer's left): lift that forearm to just below chest and open the palm gently UPWARD and angled toward the adjacent demonstration on viewer's LEFT, like a weathercaster introducing the chart beside her. Keep the complete hand inside the central 75 percent of image width, minimum 120px side margin, five relaxed natural fingers. Do not point one index finger or wave hello. The other hand rests at waist. Both arms remain below chest, hands nowhere near face.
> Preserve her EXACT recognizable face, upright head position/size, hair, expression and eye contact, navy blazer, ivory blouse, standing posture, waist-up framing, room and lighting. No camera change, no added object, no text or graphics. Same 1024x1536 portrait.

## 동작 배치와 재생

작업 폴더: `.local/product-demo/presenter-standing-20261019`.
`narration/`의10개 WAV와 `voice.json`은 기존 한국어 F2 출력을 그대로 복사했다.
`inputs.json`은 음성·원본·특징 해시, `gesture-open/report.json`,
`gesture-screen/report.json`은 실제 생성 조건을 기록한다.
각 `acceptance.json`은 시각 검토와 전체 프레임 해시를 보존한다.

두 종류의 설명 동작은 각각 중립 → 설명 → 중립 자세를 연결한다.
`timeline.json`으로0·16·35·56·76초에 배치한다. 짧은 두 동작을 여러 장면에서
재사용하며, 사이에는 마지막 휴식 자세를 유지하고 얼굴 발화를 계속 생성한다.
90초 전체의 새로운 몸 동작이나 실시간 대화를 생성했다는 뜻이 아니다.
구간 이동·정지·음성·아바타는 하나의 MP4 시계를 사용한다.

합성은2640×1080(원래 시연1920 + 아바타720)이다. 2:3 아바타를720×1080으로
비율대로 확대해 손끝을 자르지 않는다. 자막은 좌측 시연 영역에 배치한다.
아바타를 꺼도 `intro-screen.mp4`의 같은 한국어 여성 음성을 사용한다.
이전 원본 `intro.mp4`는 보존한다.

## 다시 제작하기

기존 로컬 연구 환경의 절대 경로를 실행기 변수에 지정하고 새 작업 폴더를 사용한다.
음성이 같고 화면만 바뀌면 기존 무음 아바타와 다시 합성하면 된다. 음성·장면 길이를
바꾸면 분석과 얼굴 발화를 다시 생성한다. 인물이 바뀌면 얼굴 등록과 몸 동작도 바꾼다.

```powershell
& $cpuOnnxPython -I scripts/product-demo/presenter.py prepare --research-root $research --work-dir $work --tutor bid3-guide --narration-dir "$work/narration" --source-config web/features/product-demo/presenter-source.json
# 두 동작 각각: source/end는 standing-neutral.png, middle은 각 설명 자세.
& $bodyPython -I scripts/product-demo/gesture.py --research-root $research --source-image $neutral --middle-image $middle --end-image $neutral --character "BID3 standing presenter" --prompt-file $motionPrompt --output $candidate
# 실제 손/얼굴/연속성을 검토하고 acceptance.json을 기록한 후 timeline.json에 배치한다.
& $avatarPython -I scripts/product-demo/presenter.py render --research-root $research --work-dir $work --gesture-timeline "$work/timeline.json"
.\server\venv\Scripts\python.exe scripts/product-demo/compose_presenter.py --work-dir $work
.\server\venv\Scripts\python.exe scripts/product-demo/check_presenter.py --work-dir $work
```

검수되지 않은 클립, 원본/끝 자세 불일치, 프레임 변경, 겹치거나90초를 초과하는 배치는
합성하지 않는다. `acceptance.json`은 `accepted`, `video_sha256`,
전체 `frame_sha256`, 실제 `viewed_frames`, 확인 범위 `scope`를 기록한다.

## 이번 출력의 검증 범위

두 몸 동작에서 각각8개 시점, 얼굴 발화 합성에서 초반6개 시점과80초 장면을
시각 확인했다. 두 종류의7.72초 동작을 다섯 구간에 사용하며 총38.6초이고,
나머지는 중립 자세에서 얼굴 발화를 이어간다. 몸 동작은 반복 재생 루프가 아니라
명시한 장면 시간에 배치한다. 두 원본 클립을 재사용하는 점은 그대로다.

90초/2,160프레임 전체 디코딩, 단일 음성 트랙, 화면 전용/아바타 합성본의 디코딩
오디오 SHA 일치, 원래 시연 영상 보존, 원본·자막·포스터 해시와 fast-start 검사를
통과했다. production build(TypeScript 포함)와 동작 배치 검증 테스트5개를 통과했다.
실제 HTTPS에서2640×1080 재생, 자동재생 안 함,65초 이동, 일시정지 상태의 양방향
전환 시 위치 유지(차이0.000002초), 자막 readyState2와733px 화면의 가로 넘침 없음을
확인했다. 영상 byte-range는206이며 공개 포스터 SHA도 로컬 출력과 일치한다.

19.6초 실제 웹 화면에서 서 있는 상반신, 화면을 안내하는 손바닥, 좌측에만 표시되는
자막, 우측 이름표/별도 안내 문구 없음을 확인했다. 비공개 검수 파일은 작업 폴더의
`verification.json`, `browser-verification.json`, `browser-preview.png`,
`http-verification.json`이다. 미세한 손가락·입 모양과 목소리 취향의 최종 자연스러움은
사용자 검토 범위다. 다른 작업의 Gemma는 종료하지 않았다.
