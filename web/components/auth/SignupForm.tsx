"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import Input from "@/components/ui/Input";
import { API_BASE_URL } from "@/lib/api";

export default function SignupForm() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const signupData = Object.fromEntries(formData.entries());

    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/signup/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(signupData),
      });

      if (!response.ok) {
        const errors = (await response.json()) as Record<string, string[]>;
        setError(Object.values(errors).flat().join(" "));
        return;
      }

      router.push("/login");
    } catch {
      setError("회원가입 서버에 연결할 수 없습니다.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="mt-8 space-y-4 rounded-lg border border-slate-200 bg-white p-6" onSubmit={handleSubmit}>
      <Input autoComplete="username" label="아이디" name="username" placeholder="사용할 아이디" required />
      <Input autoComplete="email" label="이메일" name="email" placeholder="company@example.com" required type="email" />
      <Input autoComplete="new-password" label="비밀번호" minLength={4} name="password" placeholder="4자 이상 입력" required type="password" />
      <Input autoComplete="new-password" label="비밀번호 확인" minLength={4} name="password_confirm" placeholder="비밀번호 다시 입력" required type="password" />

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
        {isSubmitting ? "가입 중..." : "가입하기"}
      </button>
    </form>
  );
}
