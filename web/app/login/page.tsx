import Link from "next/link";
import Header from "@/components/layout/Header";
import LoginForm from "@/components/auth/LoginForm";

export default function LoginPage() {
  return (
    <main className="min-h-screen bg-transparent text-slate-950">
      <Header />
      <section className="mx-auto w-full max-w-md px-4 py-12 sm:px-6 sm:py-16">
        <div className="text-center">
          <h1 className="text-2xl font-bold">로그인</h1>
          <p className="mt-2 text-sm text-slate-600">가입한 아이디와 비밀번호를 입력해 주세요.</p>
        </div>

        <LoginForm />

        <p className="mt-5 text-center text-sm text-slate-600">
          계정이 없다면 <Link className="font-semibold text-blue-600" href="/signup">회원가입</Link>
        </p>
      </section>
    </main>
  );
}
