# 학원 노트북에서 BID3 사용하기

개인 노트북에서 웹·Django·Ollama를 실행하고 Tailscale Serve로 웹 하나만 공유합니다.
외부 서버에 배포하지 않습니다. 두 기기가 같은 Tailscale 네트워크에 연결되어 있어야 합니다.

## 개인 노트북 시작

VS Code에서 BID3 폴더를 열고 PowerShell 터미널 두 개를 사용합니다.

첫 번째 터미널:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Start-Bid3.ps1 -Service api
```

두 번째 터미널:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\Start-Bid3.ps1 -Service web
```

두 터미널을 유지하고 Ollama도 실행합니다. 이미 서버가 실행 중이라면 중복 실행하지 않습니다.
노트북이 절전·종료 상태가 되면 접속과 생성이 중단됩니다.

처음 공유할 때만 별도 터미널에서 실행합니다. 기존 Serve 구성이 있다면 먼저 확인합니다.
```powershell
& 'C:\Program Files\Tailscale\tailscale.exe' serve status
& 'C:\Program Files\Tailscale\tailscale.exe' serve --bg http://127.0.0.1:3000
```

출력되는 `https://기기이름.tail....ts.net/` 주소가 접속 주소입니다.
`--bg` 설정은 유지되지만 BID3 서버와 Ollama는 별도로 실행해야 합니다.
HTTPS를 처음 활성화할 때 Tailscale이 안내하는 계정 설정이 필요할 수 있습니다.

## 학원 노트북 사용

1. Tailscale이 Connected인지 확인합니다.
2. 위 HTTPS 주소를 브라우저에서 열고 기존 BID3 계정으로 로그인합니다. localhost에서의 로그인과 별도입니다.
3. 왼쪽 메뉴의 **발표자료 작성하기 → + 새 발표자료 → 작업 중인 PPTX 이어서**를 선택합니다.
4. 학원 노트북의 PPTX를 업로드하고 작업실을 만듭니다. 원본은 첫 버전으로 보관됩니다.
5. 유지할 페이지를 보호하고 양식 사용을 확인한 뒤 Gemma4와 작업합니다.

브라우저의 파일 업로드는 학원 노트북의 파일을 선택합니다.
반면 참고자료의 **로컬 경로**는 서버인 개인 노트북의 경로를 뜻합니다.
학원 노트북의 자료는 파일 업로드나 내용 붙여넣기를 사용하세요.
원격 접속에서도 생성은 개인 노트북의 Gemma4에서 실행됩니다.

## 연결 구조와 종료

브라우저 → Tailscale HTTPS → 개인 노트북 Next.js 127.0.0.1:3000 → Django 127.0.0.1:8000.
웹의 `/api/` 요청을 Next.js가 전달하므로 원격 브라우저가 자신의 localhost를 호출하지 않습니다.
Ollama/API 포트를 추가로 공유하거나 공유기 포트포워딩을 설정할 필요가 없습니다.
Serve는 tailnet 접근 정책을 따릅니다. 공개 인터넷에 노출하는 Funnel은 사용하지 않습니다.

공유만 끄려면:
```powershell
& 'C:\Program Files\Tailscale\tailscale.exe' serve --https=443 off
```

개발은 `web` 폴더의 `npm run dev`로도 가능합니다. Django는 별도 실행합니다.
기본 API 모드는 동일 출처 프록시입니다. API를 다른 서버에 따로 배포할 때만
`NEXT_PUBLIC_API_MODE=direct`와 `NEXT_PUBLIC_API_BASE_URL`을 지정하고 다시 빌드합니다.
프록시 서버 주소는 `BID_API_BASE_URL`입니다.

## 검증 기록 (2026-09-25)

- production build 및 ESLint 통과.
- 실제 Tailscale HTTPS 주소에서 임시 계정 로그인, 인증 API, PATCH 통과.
- 12MB 이상의 PPTX multipart 업로드와 바이트 단위로 동일한 다운로드 확인.
- 테스트 계정과 업로드 파일 정리. 실제 사용자 자료는 이 테스트에서 사용하지 않음.
- 이 검증은 개인 노트북에서 공유 주소를 호출한 결과이며, 학원 브라우저 접속은 별도 확인 필요.

공식 안내: https://tailscale.com/docs/features/tailscale-serve
