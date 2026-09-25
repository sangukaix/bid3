# Windows 실행 및 같은 네트워크에서 팀원 접속

이미 설치된 이 노트북에서는 재설치나 DB 초기화 없이 실행한다.
Ollama 앱을 먼저 실행한다. 모델은 호스트 노트북에서 실행되며 팀원 PC에 설치할 필요가 없다.

## 같은 네트워크 공유

노트북의 Wi-Fi IPv4 주소는 `ipconfig`에서 확인한다.
2026-09-17 확인 주소는 `192.168.50.92`이며 네트워크가 바뀌면 달라질 수 있다.

PowerShell 창 두 개를 열고 각각 실행한다. 두 명령의 Address는 동일해야 한다.

첫 번째 창(API):

```powershell
cd D:\pp2026\bid3
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Bid3.ps1 -Service api -Address 192.168.50.92
```

두 번째 창(웹):

```powershell
cd D:\pp2026\bid3
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\Start-Bid3.ps1 -Service web -Address 192.168.50.92
```

웹 빌드가 끝나 Ready가 표시되면 본인과 팀원 모두 `http://192.168.50.92:3000`으로 접속한다.
팀원은 localhost가 아닌 이 노트북의 주소를 사용한다.
두 터미널을 열어 둔다. 종료는 각 창에서 Ctrl+C.
노트북이 꺼지거나 절전 상태로 들어가면 접속할 수 없다.

스크립트는 실행 프로세스에만 API 주소/허용 호스트/CORS를 설정한다.
.env와 기존 데이터는 덮어쓰지 않는다. 공개 API 주소는 웹 빌드에 포함되므로 웹 실행 시 다시 빌드한다.
기존 서버가 같은 포트를 사용 중이면 종료 후 실행한다.

## 개인 노트북에서만 실행

위 두 명령의 `-Address 192.168.50.92`를 빼면 루프백으로만 실행한다.
접속 주소는 `http://127.0.0.1:3000`이다. 공유 모드에서 개인 모드로 바꿀 때도 웹을 다시 빌드한다.

## 팀원 PC에서 연결되지 않을 때

1. 같은 공유기/내부망에 연결돼 있는지 확인한다. 게스트 Wi-Fi는 기기 간 통신을 차단할 수 있다.
2. 두 서버가 실행 중인지, 노트북 IPv4 주소가 바뀌지 않았는지 확인한다.
3. Windows 방화벽이 차단한다면 관리자 PowerShell에서 아래 규칙을 한 번 추가한다.
   이 규칙은 Private 네트워크의 같은 서브넷에서만 3000/8000 포트를 허용한다.

```powershell
New-NetFirewallRule -DisplayName "BID3 Team LAN" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 3000,8000 -Profile Private -RemoteAddress LocalSubnet
```

규칙 제거:

```powershell
Remove-NetFirewallRule -DisplayName "BID3 Team LAN"
```

Ollama의 11434 포트를 팀원에게 개방할 필요는 없다.
팀원은 웹에서 본인 계정으로 로그인한다. 관리자 유지보수 화면은 기존 관리자 권한으로 제한된다.

## 현재 제한

이 실행 방식은 팀 내부 테스트용 Django 개발 서버와 Next 프로덕션 실행을 사용한다.
장기 상시 운영용 배포 구성은 별도다. 동시에 여러 명이 AI를 사용하면 이 노트북의 GPU 처리 순서를 기다릴 수 있다.
로컬 제안서 생성은 페이지별 원문 선택과 응답 캐시를 사용한다. 생성 문서에는 요구사항 누락·회사 증빙 미확인 등 품질 문제가 남아 있으므로 제출 전 보완이 필요하다. 최신 검증은 [2026-09-25 기록](LOCAL_AI_VALIDATION_2026-09-25.md)을 참고한다.
