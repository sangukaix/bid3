"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { API_BASE_URL } from "@/lib/api";

export default function LogoutButton() {
  const router = useRouter(); // 로그아웃 후 로그인 페이지로 이동
  const [isLoggingOut, setIsLoggingOut] = useState(false); // 중복 클릭 방지 상태

  async function handleLogout() {
    const token = localStorage.getItem("auth_token"); // 로그인할 때 저장한 인증표
    setIsLoggingOut(true);

    try {
      if (token) {
        await fetch(`${API_BASE_URL}/api/auth/logout/`, {
          method: "POST",
          headers: { Authorization: `Token ${token}` }, // Django에 로그인 사용자 전달
        });
      }
    } finally {
      localStorage.removeItem("auth_token"); // 브라우저의 로그인 인증표 삭제
      localStorage.removeItem("auth_user"); // 브라우저의 사용자 정보 삭제
      router.push("/login");
      router.refresh();
    }
  }

  return (
    <button
      className="rounded-md px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-100 disabled:text-slate-400"
      disabled={isLoggingOut}
      onClick={handleLogout}
      type="button"
    >
      {isLoggingOut ? "로그아웃 중..." : "로그아웃"}
    </button>
  );
}
