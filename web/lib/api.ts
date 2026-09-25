// 기본값은 같은 웹 주소의 프록시입니다. 원격 PC의 localhost를 호출하지 않습니다.
// 별도 API 배포를 사용하는 경우에만 direct 모드를 명시합니다.
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_MODE === "direct"
    ? (process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000")
    : "";
