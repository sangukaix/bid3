# 조이 안내 영상 제작 자료 — 2026-10-19

요청: 기존 시연 영상 오른쪽에는 조이(Zoe)와 실내 배경만 표시한다.
안내 문구·이름표·장식 패널은 제거하고 한국어 여성 음성과 짧은 손 인사를 적용한다.
조이는 Speak의 원본 가상 성인 캐릭터다. 실제 인물의 얼굴·목소리를 복제하지 않는다.

## 출처와 보존

- 기준 이미지: Speak의 `tutor-zoe-blonde-v2.png`, SHA256
  `970c45f8e8fe25746fbaa09d40297ac4f591d2777f15ba9c0e16e90b367b92e3`.
- 아래 두 제작용 파생 이미지는 내장 `image_gen` 도구로 편집했다. Speak 원본은
  수정하지 않았다. 프로젝트에 저장한 선택본:
  `web/public/product-demo/presenter/zoe-room-source.png`,
  `web/public/product-demo/presenter/zoe-room-neutral.png`.
- 음성: Supertonic2 기본 F2 여성 스타일, 한국어 `ko`, 속도1.13,12steps.
  유명인/사용자 음성 복제가 아니다. 공식 모델
  [Supertone/supertonic-2](https://huggingface.co/Supertone/supertonic-2),
  revision `75e6727618a02f323c720cba9478152d4bc16ca4`, CPU ONNX.
  `supertonic==1.3.1`은 별도 `.local/product-demo/tts-venv`에 설치했다.
  모델 파일은 `.local/product-demo/supertonic2`에 저장하고 배포/소스에 넣지 않는다.
- Edge 온라인 음성은403으로 실패해 사용하지 않았다. 실패 후 접근 제한을 우회하지
  않았으며, 실제 배포 음성은 로컬 합성이다. OpenAI API 키를 사용하지 않았다.
- 동작: 기존 로컬 LTX-Video2B0.9.6distilled, 얼굴 발화: 기존 Ditto/HuBERT/렌더러.
  모델·코드의 정확한 해시는 연구 환경의 기존 매니페스트와 새 출력 기록으로 확인한다.
  이 자료는 전체 모델 체인의 상업적 이용 허가를 보증하지 않는다.

## 선택본 이미지 프롬프트

실행 경로는 내장 image_gen이며, CLI/API 키 경로를 사용하지 않았다.

첫 이미지:

> Use case: identity-preserve edit. Edit target: the attached original fictional adult female AI character Zoe. Create one photorealistic production still for a calm presenter animation. Preserve her exact recognizable face, freckles, adult age, short wavy blonde bob, eye color, body proportions, and blue linen shirt worn open over the same plain white top. No beautification or different identity. Frame from head to below the waist, with head fully visible and BOTH COMPLETE HANDS clearly inside the frame. She is seated facing the camera. Her right forearm is lifted gently, elbow bent, with her right hand at lower chest height in a natural relaxed open greeting pose; five normal separate fingers. Her left hand rests naturally on her lap and is fully visible. Keep all fingers well below the chin, without face occlusion. Warm closed-mouth smile, direct eye contact. Set her in a quiet softly daylit real room with a warm grey/ivory wall, subtle depth, a softly out-of-focus small plant at the far side and restrained home-office feel; no furniture obstructing her hands. Match the original natural light and realistic skin, avoid glamor retouching. Portrait 2:3 composition. The output is only the woman and the room background: absolutely NO text, labels, captions, logo, borders, nameplate, graphic overlays, or interface.

마지막 자세 이미지:

> Identity-preserving precise pose edit of this SAME original fictional adult woman Zoe. This image is the final resting keyframe of a short hand greeting. Change ONLY her raised right arm/hand pose: gently lower her right forearm and place her right hand naturally on her lap beside her existing left hand, with both complete hands relaxed and visible. Preserve the same exact face, freckles, hair, expression, eye contact, blue linen shirt, white top, seated position, camera, framing, lighting, chair and room background. Keep her head in exactly the same location and size. No new gesture or objects. No text, borders, graphics or labels. Same 2:3 portrait composition. Both arms should now rest naturally, neither hand is raised.

## 제작 및 검증 기록

이번 작업 폴더는 `.local/product-demo/presenter-zoe-20261019`다. 이전 Alex 출력과
원본 소개 영상은 보존한다. `narration-v2/voice.json`은 음성별 길이·해시·합성 조건,
`inputs.json`은 대응 음성과 조이 원본·등록 좌표, `gesture-keyframes/report.json`은
동작 조건, `acceptance.json`은 채택 여부와 프레임 해시를 보존한다.
실패하거나 채택하지 않은 동작 후보를 완성 손짓으로 설명하지 않는다.

손 인사는 도입부의 제한된 구간이며, 나머지는 휴식 자세에서 설명하는 구성이다.
동작을 반복 재생하거나 전체90초가 실시간으로 생성된다고 설명하지 않는다.
화면만 보기와 아바타 보기 모두 같은 한국어 여성 음성을 사용한다.
`check_presenter.py`는 두 버전의 오디오 동일성·트랙1개·전체 디코딩·소스 해시를 확인한다.

## 이번 출력의 확인 범위

조이+실내 배경 이외의 우측 그래픽을 제거했다. 도입부7.72초의 서로 다른193개
몸 동작 프레임에서 손 인사 후 손을 내리는 구간을 사용하고, 이후에는 마지막
휴식 자세를 바탕으로 얼굴 발화를 계속 생성한다. 몸 동작을 반복 재생하지 않는다.
8개 몸 동작 시점과6개 발화 시점을 시각 검수했고, 실제 웹에서 손 인사와 자막이
좌측 화면에만 표시되는 것을 확인했다. 미세한 손가락·입 모양과 목소리 취향의
최종 자연스러움은 사용자 검토 범위다.

90초2,160프레임 전체 디코딩, 화면 전용/조이 합성본의 새 한국어 오디오 SHA 일치,
오디오1개, 원래 시연 MP4 보존, 자막·소스 해시, byte-range206, lint·TypeScript·
production build를 통과했다. 실제 HTTPS에서 자동재생 안 함,65초 장면 이동,
일시정지 상태의 아바타 전환 시 위치 차이0초, 자막 readyState2, 가로 넘침 없음,
비로그인 회사 API401을 확인했다. 실제 웹 캡처와 JSON은 작업 폴더의
`browser-preview.png`, `browser-verification.json`, `verification.json`에 있다.
Gemma는 자연 만료로 GPU를 반환했으며 다른 프로젝트의 모델을 강제 종료하지 않았다.

## 다음 수정 시

정적인 얼굴 등록 좌표와 출처는 `web/features/product-demo/presenter-source.json`에
있다. 새로운 작업 폴더를 지정해 이전 결과를 보존한다. 모델 경로·실행기는 기존
별도 환경을 지정한다. 내레이션과 장면 길이가 같으면 기존 무음 아바타 트랙으로
화면만 다시 합성할 수 있다. 음성을 바꾸면 음성 분석·얼굴 발화를 다시 출력한다.

```powershell
& $ttsPython scripts/product-demo/narrate_local.py --download --model-dir .local/product-demo/supertonic2 --output "$work/narration"
& $cpuOnnxPython -I scripts/product-demo/presenter.py prepare --research-root $research --work-dir $work --tutor zoe --narration-dir "$work/narration" --source-config web/features/product-demo/presenter-source.json
# 손 인사를 다시 만들 때만 실행한다. 출력과 손 모양을 검토한 후 acceptance.json을 기록한다.
& $bodyPython -I scripts/product-demo/gesture.py --research-root $research --source-image web/public/product-demo/presenter/zoe-room-source.png --end-image web/public/product-demo/presenter/zoe-room-neutral.png --output "$work/gesture"
& $avatarPython -I scripts/product-demo/presenter.py render --research-root $research --work-dir $work --gesture-dir "$work/gesture"
.\server\venv\Scripts\python.exe scripts/product-demo/compose_presenter.py --work-dir $work
.\server\venv\Scripts\python.exe scripts/product-demo/check_presenter.py --work-dir $work
```

`acceptance.json`은 검토를 마친 후보의 `accepted`, `video_sha256`, 순서대로193개
`frame_sha256`, 실제 확인한 `viewed_frames`, 검토 범위 `scope`를 기록한다.
해시가 다르거나 채택 기록이 없으면 얼굴/몸 합성을 진행하지 않는다.
