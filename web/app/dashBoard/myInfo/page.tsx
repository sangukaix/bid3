"use client";

import Link from "next/link";
import { useSyncExternalStore } from "react";

import PageHeader from "@/components/layout/PageHeader";

const plans = [
  { name: "Free", price: "0원", analysis: "월 3회", proposal: "제공 안 함", chat: "기본 AI 채팅" },
  { name: "Plus", price: "월 10,000원", analysis: "월 20회", proposal: "월 2회", chat: "확장 AI 채팅" },
  { name: "Pro", price: "월 50,000원", analysis: "월 100회", proposal: "월 10회", chat: "고용량 AI 채팅" },
];

function subscribeToAuth(onChange: () => void) {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

function getAuthSnapshot() {
  return Boolean(localStorage.getItem("auth_token"));
}

export default function MyInfoPage() { // /dashBoard/myInfo 주소에서 보이는 결제 정보 페이지
  const isLoggedIn = useSyncExternalStore(
    subscribeToAuth,
    getAuthSnapshot,
    () => false,
  ); // localStorage 로그인 상태를 React 방식으로 읽음

  if (!isLoggedIn) {
    return (
      <section className="border-y border-slate-200 py-10 text-center">
        <p className="text-sm text-red-600">로그인 후 확인이 가능합니다.</p>
        <Link className="mt-4 inline-flex rounded-md bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" href="/login">
          로그인
        </Link>
      </section>
    );
  }

  return (
    <section className="min-w-0">
      <PageHeader description="현재 요금제와 월별 제공량, 결제 내역을 확인합니다." title="결제 정보" />

      <section className="app-panel mt-6 overflow-hidden rounded-lg border">
        <div className="grid gap-6 p-6 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
          <div>
            <p className="text-xs font-semibold text-blue-700">현재 이용 중</p>
            <div className="mt-2 flex flex-wrap items-end gap-x-3 gap-y-1">
              <h2 className="text-2xl font-bold text-slate-950">Free</h2>
              <p className="pb-0.5 text-sm text-slate-500">0원 / 월</p>
            </div>
            <p className="mt-3 text-sm text-slate-600">매월 AI 공고 분석 3회가 제공되며 자동 결제는 발생하지 않습니다.</p>
          </div>
          <button className="rounded-md border border-slate-300 bg-white px-4 py-2.5 text-sm font-semibold text-slate-400" disabled type="button">
            요금제 변경 준비 중
          </button>
        </div>

        <dl className="grid border-t border-slate-200 bg-slate-50/70 sm:grid-cols-3 sm:divide-x sm:divide-slate-200">
          <div className="p-5">
            <dt className="text-xs text-slate-500">AI 공고 분석</dt>
            <dd className="mt-2 text-base font-semibold text-slate-900">월 3회 제공</dd>
          </div>
          <div className="border-t border-slate-200 p-5 sm:border-t-0">
            <dt className="text-xs text-slate-500">제안서 작성</dt>
            <dd className="mt-2 text-base font-semibold text-slate-900">제공 안 함</dd>
          </div>
          <div className="border-t border-slate-200 p-5 sm:border-t-0">
            <dt className="text-xs text-slate-500">다음 결제일</dt>
            <dd className="mt-2 text-base font-semibold text-slate-900">자동 결제 없음</dd>
          </div>
        </dl>
      </section>

      <section className="app-panel mt-6 grid overflow-hidden rounded-lg border lg:grid-cols-2 lg:divide-x lg:divide-slate-200">
        <div className="p-6">
          <h2 className="text-base font-bold text-slate-950">결제수단</h2>
          <p className="mt-3 text-sm text-slate-600">등록된 결제수단이 없습니다.</p>
          <button className="mt-4 rounded-md border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-400" disabled type="button">
            카드 등록 준비 중
          </button>
        </div>
        <div className="border-t border-slate-200 p-6 lg:border-t-0">
          <h2 className="text-base font-bold text-slate-950">결제 주기</h2>
          <p className="mt-3 text-sm text-slate-600">유료 플랜은 한 달 단위 정기 구독으로 제공할 예정입니다.</p>
          <p className="mt-2 text-xs leading-5 text-slate-500">플랜 변경과 해지는 결제 기능 연결 후 이 화면에서 관리할 수 있습니다.</p>
        </div>
      </section>

      <section className="app-panel mt-6 overflow-hidden rounded-lg border">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-base font-bold text-slate-950">요금제 비교</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="px-5 py-3 font-semibold">플랜</th>
                <th className="px-5 py-3 font-semibold">월 요금</th>
                <th className="px-5 py-3 font-semibold">AI 공고 분석</th>
                <th className="px-5 py-3 font-semibold">제안서 작성</th>
                <th className="px-5 py-3 font-semibold">AI 채팅</th>
                <th className="px-5 py-3 text-right font-semibold">상태</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {plans.map((plan) => (
                <tr className={plan.name === "Free" ? "bg-blue-50/50" : "bg-white"} key={plan.name}>
                  <td className="px-5 py-4 font-semibold text-slate-950">{plan.name}</td>
                  <td className="px-5 py-4 text-slate-700">{plan.price}</td>
                  <td className="px-5 py-4 text-slate-700">{plan.analysis}</td>
                  <td className="px-5 py-4 text-slate-700">{plan.proposal}</td>
                  <td className="px-5 py-4 text-slate-700">{plan.chat}</td>
                  <td className="px-5 py-4 text-right">
                    <span className={`inline-flex rounded-md px-2.5 py-1 text-xs font-semibold ${
                      plan.name === "Free" ? "bg-blue-100 text-blue-700" : "bg-slate-100 text-slate-500"
                    }`}>
                      {plan.name === "Free" ? "현재 플랜" : "준비 중"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="app-panel mt-6 overflow-hidden rounded-lg border">
        <div className="border-b border-slate-200 px-5 py-4">
          <h2 className="text-base font-bold text-slate-950">결제 내역</h2>
        </div>
        <div className="px-5 py-10 text-center">
          <p className="text-sm text-slate-500">아직 결제 내역이 없습니다.</p>
        </div>
      </section>
    </section>
  );
}
