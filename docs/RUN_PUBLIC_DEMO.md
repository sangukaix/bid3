# 초대받은 선생님에게 인터넷으로 BID3 공유하기

개인 노트북에서 Next.js·Django·Gemma를 실행하고 웹을 Cloudflare Quick Tunnel로 공유한다. **첫 화면은 초대 암호 없이 열고, 회사 자료·제안서·발표자료 작업은 BID3 계정으로 로그인한다.** 선생님은 같은 IP·와이파이나 Tailscale 설치 없이 HTTPS 주소로 접속한다. Vercel이나 외부 GPU 서버로 자료를 이전하는 배포는 아니다.

기존 개인용 Tailscale 443번 Serve는 비공개로 유지한다. 선생님용은 **Cloudflare HTTPS → 127.0.0.1:3002 → 127.0.0.1:8002**로 분리한다. Django는 Waitress로 실행하고 DEBUG를 끈다. API·Ollama·노트북 파일 폴더를 직접 공개하지 않는다. 개인용 3001/8000과 공개용 3002/8002는 기존 DB·업로드·모델 설정을 공유한다. 원본을 복제하거나 초기화하지 않는다.

Quick Tunnel은 계정·도메인 없이 사용하는 **임시 개발·시연 연결**이다. 프로세스가 종료되면 주소가 끊기고 다시 만들면 주소가 바뀐다. 상시 운영 보장은 없다. [Cloudflare 공식 안내](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)를 참고한다. 고정 주소·정식 운영용 배포는 별도 작업이다.

## 준비

프로젝트 루트에서 작업한다. `cloudflared.exe`가 PATH에 있어야 한다. 이 노트북에서는 이미 설치된 Cloudflare 프로그램을 사용했다. 새 PC라면 공식 설치 안내를 따른다.

```powershell
cd D:\pp2026\bid3
.\server\venv\Scripts\python.exe -m pip install -r .\server\requirements.txt
```

최초 실행은 `.local/public-demo/access.json`에 임의의 초대 암호·세션 서명 키·공개 API용 Django secret을 생성한다. 현재 Windows 사용자와 SYSTEM만 접근하도록 폴더 권한을 제한한다. 기존 `.env`는 덮어쓰지 않는다. 해당 파일과 안내문은 Git·ZIP·공개 자료에 넣지 않는다. 실행 스크립트는 Windows PowerShell 5.1의 한글 처리를 위해 UTF-8 BOM으로 저장한다.

## 실행 순서

Ollama를 켜고 **터미널 3개**를 사용한다. 기존 공개 시연이 실행 중이면 중복 실행하지 않는다.

첫 번째 터미널 — 새 임시 HTTPS 주소가 표시될 때까지 기다린다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Bid3PublicDemo.ps1 -Service tunnel
```

처음 준비하거나 웹 코드가 바뀌었을 때만 별도 터미널에서 빌드한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Bid3PublicDemo.ps1 -Service build
```

개인용 `.next`를 건드리지 않고 `.next-public-demo`를 만든다. 공개용 빌드는 런타임 공개 플래그를 빠뜨려도 암호·서명 키 설정이 없으면 503으로 닫힌다. 일반 개인용 빌드는 기본적으로 초대 기능을 켜지 않는다.

두 번째 터미널 — 공개 API:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Bid3PublicDemo.ps1 -Service api
```

세 번째 터미널 — 공개 웹:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Bid3PublicDemo.ps1 -Service web
```

API·웹 시작 시 프로젝트 전용 터널 로그에서 새 HTTPS 주소를 읽어 현재 origin과 안내문을 갱신한다. 터널을 다시 시작해 주소가 바뀌면 **공개 API와 웹도 다시 실행**한다. 다른 프로젝트의 cloudflared 프로세스·사용자 설정은 변경하지 않는다.

## 선생님에게 전달

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Bid3PublicDemo.ps1 -Service info
```

출력된 `.local/public-demo/선생님_접속안내.txt`에 현재 주소가 있다. 서명 키나 `access.json` 전체를 전달하지 않는다.

1. 선생님은 주소를 바로 연다. 현재 초대 암호는 요구하지 않는다.
2. BID3에 로그인하거나 본인 계정을 가입한다.
3. 본인 자료로 제안서·발표자료를 사용한다. 기존 test1 자료를 다른 계정에 자동 공유하지 않는다.

새 설정의 `require_invitation`은 `false`다. 기존 설정은 이 항목을 명시적으로 `false`로 바꿔야 초대 암호를 해제한다. 누락 시 기존 초대 모드를 유지한다. 공개용 웹 런타임에는 `BID3_DEMO_REQUIRE_INVITE=0`을 전달하며, 설정 자체가 없으면 기존처럼 503을 반환한다. 초대 모드를 다시 켜면 Secure·HttpOnly·SameSite=Strict 서명 쿠키로 8시간 유지하며 틀린 암호는 1분 10회 실패로 제한한다.

공개 API는 `BID3_PUBLIC_WEB=1`로 실행한다. 로그인은 사용자명당 1분 8회·전체 1분 60회, 회원가입은 전체 1시간 10회로 제한한다. 위조 가능한 전달 IP를 제한 키로 사용하지 않는다. 새 비밀번호는 Django의 최소 8자·흔한 비밀번호·숫자 전용 검사를 통과해야 한다. 기존 계정 비밀번호는 변경하지 않는다. 카운터는 단일 프로세스 메모리 기준이며, 소수의 시연 접속을 위한 구성이다.

노트북 절전·종료 또는 터널/웹/API 종료 시 접속·작업이 중단된다. **재부팅 후 자동 시작을 등록한 것은 아니므로 위 실행 순서를 다시 진행한다.** 여러 사람이 생성하면 같은 로컬 GPU를 공유한다. 임시 연결에는 동시 요청 제한·SSE 미지원 등이 있다. 현재 상태 조회는 일반 HTTP 폴링을 사용하며 이번 접속 시험이 모든 장시간 AI 요청의 성공을 보장하지는 않는다.

## 종료

공개용 터미널 3개에서 각각 Ctrl+C로 종료한다. 개인용 서버나 다른 프로젝트를 일괄 종료하지 않는다. 기존 개인용 Tailscale 공유 설정은 그대로 유지한다.

## 2026-10-18 확인과 전환 사유

처음에는 Tailscale Funnel의 8443번 공개 주소를 구성했으나, CLI가 공개 상태를 표시해도 일반 공개 DNS는 10분 이상 NXDOMAIN을 반환했다. 내부 접속 성공을 인터넷 성공으로 취급하지 않고 설치된 cloudflared의 임시 연결로 전환했다. 진단 중 잠시 변경한 443번은 개인용 Serve로 복원했고 8443번 Funnel은 껐다. 현재 Tailscale은 `tailnet only`다.

초대 모드에서 Cloudflare 주소의 공개 DNS와 전역 IP로 HTTPS 접속을 확인했다. 당시 초대 화면 200, 암호 없는 메인 307, 회사 API 401이었다. 로컬과 공유 HTTPS의 접근·다운로드 23건씩도 통과했다. 소유자 조회 200, 계정 토큰 없는 회사 자료 401, 일반 계정 유지보수 403, 다른 소유자 제안서·원문 404, 미확정 최종본 다운로드 409였다. 초대 해제 후에는 별도 기록 `open-*-verification.json`으로 쿠키 없는 메인 200, 이전 초대 화면의 메인 이동, 계정별 접근 제한을 다시 확인한다. 과거 초대 화면 캡처는 현재 화면을 뜻하지 않는다.

웹 ESLint·TypeScript·production build, 초대 암호·서명·만료·키 변경 검사, 연속 오입력 제한, 공개 빌드에 플래그·암호가 빠졌을 때의 503을 확인했다. 브라우저 초대 접속·시험 계정 로그인·공고 목록·로그아웃과 합성 PPTX 업로드·동일 바이트 다운로드를 확인했다. 시험 프로젝트는 보관하고 시험 계정은 비활성화·토큰 폐기한다. 회사 원문·기존 21쪽 출력 SHA는 보존한다. 시점별 주소·실행 증거는 비공개 `.local/public-demo/`에 기록한다. 선생님 PC의 실제 브라우저 시험은 별도다.
