import Link from "next/link";

export default function LoginRequiredNotice() {
  return (
    <div className="mt-6 py-10 text-center">
      <p className="text-sm text-red-600">로그인 후 확인이 가능합니다.</p>
      <Link className="mt-4 inline-flex rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white" href="/login">
        로그인
      </Link>
    </div>
  );
}
