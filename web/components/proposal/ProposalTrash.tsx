"use client";

import { useEffect, useState } from "react";

import LoginRequiredNotice from "@/components/auth/LoginRequiredNotice";
import { API_BASE_URL } from "@/lib/api";
import type { BidNotice, SavedBidResponse } from "@/types/bid";

export default function ProposalTrash() {
  const [items, setItems] = useState<BidNotice[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [needsLogin, setNeedsLogin] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    async function loadTrash() {
      const token = localStorage.getItem("auth_token");
      if (!token) {
        setNeedsLogin(true);
        setIsLoading(false);
        return;
      }
      try {
        const response = await fetch(`${API_BASE_URL}/api/proposal-trash/`, {
          headers: { Authorization: `Token ${token}` },
        });
        if (response.status === 401 || response.status === 403) {
          setNeedsLogin(true);
          return;
        }
        if (!response.ok) throw new Error();
        const data = (await response.json()) as SavedBidResponse;
        setItems(data.items);
      } catch {
        setMessage("휴지통을 불러오지 못했습니다.");
      } finally {
        setIsLoading(false);
      }
    }

    void loadTrash();
  }, []);

  async function restoreProject(bidNtceNo: string) {
    const token = localStorage.getItem("auth_token");
    if (!token) return;
    const response = await fetch(
      `${API_BASE_URL}/api/saved-bids/${encodeURIComponent(bidNtceNo)}/proposal-project/restore/`,
      {
        method: "POST",
        headers: { Authorization: `Token ${token}` },
      },
    );
    if (!response.ok) {
      setMessage("프로젝트를 복원하지 못했습니다.");
      return;
    }
    setItems((current) =>
      current.filter((item) => item.bidNtceNo !== bidNtceNo),
    );
    setMessage("프로젝트를 목록의 마지막 순서로 복원했습니다.");
    window.dispatchEvent(new Event("proposal-projects-updated"));
  }

  async function deletePermanently(bidNtceNo: string) {
    const confirmed = window.confirm(
      "프로젝트의 제안서, 채팅, 분석 자료가 모두 삭제되며 복구할 수 없습니다. 영구 삭제하시겠습니까?",
    );
    if (!confirmed) return;

    const token = localStorage.getItem("auth_token");
    if (!token) return;
    const response = await fetch(
      `${API_BASE_URL}/api/saved-bids/${encodeURIComponent(bidNtceNo)}/proposal-project/permanent/`,
      {
        method: "DELETE",
        headers: { Authorization: `Token ${token}` },
      },
    );
    if (!response.ok) {
      setMessage("프로젝트를 영구 삭제하지 못했습니다.");
      return;
    }
    setItems((current) =>
      current.filter((item) => item.bidNtceNo !== bidNtceNo),
    );
    setMessage("프로젝트를 영구 삭제했습니다. 저장 공고는 유지됩니다.");
    window.dispatchEvent(new Event("proposal-projects-updated"));
  }

  if (needsLogin) return <LoginRequiredNotice />;

  return (
    <section className="app-panel mt-6 overflow-hidden rounded-lg border">
      {message && (
        <p className="border-b border-slate-200 bg-slate-50 px-5 py-3 text-sm text-slate-600">
          {message}
        </p>
      )}
      {isLoading ? (
        <p className="px-5 py-14 text-center text-sm text-slate-500">
          휴지통을 불러오는 중입니다.
        </p>
      ) : items.length === 0 ? (
        <p className="px-5 py-14 text-center text-sm text-slate-500">
          휴지통이 비어 있습니다.
        </p>
      ) : (
        <div className="divide-y divide-slate-200">
          {items.map((item) => (
            <article
              className="grid gap-4 px-5 py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"
              key={item.bidNtceNo}
            >
              <div className="min-w-0">
                <p className="truncate text-sm font-semibold text-slate-900">
                  {item.bidNtceNm}
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  {item.bsnsDivNm || "구분 확인 필요"} · 휴지통 이동 {item.proposalTrashedAt?.slice(0, 10)}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  className="cursor-pointer rounded-md border border-blue-200 px-3 py-2 text-xs font-semibold text-blue-700 hover:bg-blue-50"
                  onClick={() => void restoreProject(item.bidNtceNo)}
                  type="button"
                >
                  복원
                </button>
                <button
                  className="cursor-pointer rounded-md border border-red-200 px-3 py-2 text-xs font-semibold text-red-600 hover:bg-red-50"
                  onClick={() => void deletePermanently(item.bidNtceNo)}
                  type="button"
                >
                  영구 삭제
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
