# Bid2 Web

나라장터 공고 검색, 저장, AI 채팅/분석, 제안서 생성을 제공하는 Next.js
프론트엔드입니다.

## 실행

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

브라우저에서 `http://localhost:3000`을 엽니다. API 기능을 사용하려면 Django
서버가 `http://127.0.0.1:8000`에서 함께 실행 중이어야 합니다.

## 구조

```text
app/          URL과 공통 레이아웃
components/   재사용 React 컴포넌트
lib/          공통 API 주소와 데이터 표시 함수
types/        Django API 응답 자료형
public/       정적 파일
```
