// 브라우저에서 Django API를 호출할 때 사용하는 공통 주소입니다.
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
