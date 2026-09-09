import Link from "next/link";
import Header from "@/components/layout/Header";
import SignupForm from "@/components/auth/SignupForm";

export default function SignupPage() {
  return (
    <main className="min-h-screen bg-transparent text-slate-950">
      <Header />
      <section className="mx-auto w-full max-w-md px-4 py-12 sm:px-6 sm:py-16">
        <div className="text-center">
          <h1 className="text-2xl font-bold">회원가입</h1>
          <p className="mt-2 text-sm text-slate-600">계정을 만든 후 회사 정보를 등록할 수 있습니다.</p>
        </div>

        <SignupForm />

        <p className="mt-5 text-center text-sm text-slate-600">
          이미 계정이 있다면 <Link className="font-semibold text-blue-600" href="/login">로그인</Link>
        </p>
      </section>
    </main>
  );
}
