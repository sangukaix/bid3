export const dynamic = "force-dynamic";

export default async function AccessPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const { error } = await searchParams;
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-100 px-5 py-12">
      <section className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
        <p className="text-xs font-semibold tracking-widest text-blue-600">AI BID · INVITED DEMO</p>
        <h1 className="mt-3 text-2xl font-bold text-slate-950">AI비드 시연 접속</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">초대받은 분을 위한 작업 공간입니다. 전달받은 접속 암호를 입력해 주세요.</p>
        <form action="/access/verify" className="mt-6 space-y-4" method="post">
          <label className="block text-sm font-semibold text-slate-700" htmlFor="demo-password">초대 암호</label>
          <input autoComplete="current-password" className="w-full rounded-lg border border-slate-300 px-3 py-3 text-base outline-none focus:border-blue-500" id="demo-password" maxLength={256} name="password" required type="password" />
          {error && <p className="text-sm text-red-700" role="alert">접속 암호를 확인해 주세요.</p>}
          <button className="w-full cursor-pointer rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-700" type="submit">시연 웹 열기</button>
        </form>
        <p className="mt-5 text-xs leading-5 text-slate-500">접속 후에는 BID3 계정으로 로그인합니다. 회사 자료와 작성 문서는 로그인한 계정별로 관리됩니다. 호스트 노트북이 켜져 있을 때 이용할 수 있습니다.</p>
      </section>
    </main>
  );
}
