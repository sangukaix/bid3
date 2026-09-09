"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import Input from "@/components/ui/Input";
import { API_BASE_URL } from "@/lib/api";

type LoginResponse = {
  token: string;
  user: {
    id: number;
    username: string;
    email: string;
  };
};

export default function LoginForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const loginData = Object.fromEntries(formData.entries());

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/login/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(loginData),
      });

      if (!response.ok) {
        const errors = (await response.json()) as Record<string, string[]>;
        setError(Object.values(errors).flat().join(" "));
        return;
      }

      const data = (await response.json()) as LoginResponse;
      localStorage.setItem("auth_token", data.token);
      localStorage.setItem("auth_user", JSON.stringify(data.user));
      router.push("/dashBoard");
    } catch {
      setError("로그인 서버에 연결할 수 없습니다.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="mt-8 space-y-4 rounded-lg border border-slate-200 bg-white p-6" onSubmit={handleSubmit}>
      <Input autoComplete="username" label="아이디" name="username" placeholder="아이디" required />
      <Input autoComplete="current-password" label="비밀번호" name="password" placeholder="비밀번호" required type="password" />

      {error && (
        <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}

      <button
        className="w-full rounded-md bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700 disabled:bg-slate-300"
        disabled={isSubmitting}
        type="submit"
      >
        {isSubmitting ? "로그인 중..." : "로그인"}
      </button>
    </form>
  );
}
