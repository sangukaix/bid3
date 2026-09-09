"use client"; // 공고 질문과 제안서 수정 요청을 한 대화창에서 관리

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { API_BASE_URL } from "@/lib/api";
import type {
  BidProposalData,
  BidProposalResponse,
} from "@/types/bid";

type ChatSource = {
  number?: number;
  file_name?: string;
  location?: string;
};

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  text: string;
  sources?: ChatSource[];
  messageType: "question" | "proposal";
  status: "applied" | "pending" | "failed";
  isDeleted: boolean;
};

type BidChatWindowProps = {
  bidNtceNo: string;
  bidTitle: string;
  embedded?: boolean;
  showHeader?: boolean;
  selectedSlide?: number;
  onClose?: () => void;
  onProposalUpdated?: (proposal: BidProposalData) => void;
};

export default function BidChatWindow({
  bidNtceNo,
  bidTitle,
  embedded = false,
  showHeader = true,
  selectedSlide,
  onClose,
  onProposalUpdated,
}: BidChatWindowProps) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pendingRevisionCount, setPendingRevisionCount] = useState(0);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [isAnswerLoading, setIsAnswerLoading] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [error, setError] = useState("");
  const messageAreaRef = useRef<HTMLDivElement>(null);

  const loadHistory = useCallback(async () => {
    const token = localStorage.getItem("auth_token");
    if (!token) {
      setError("로그인 후 AI비서를 사용할 수 있습니다.");
      setIsHistoryLoading(false);
      return;
    }

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/bids/${bidNtceNo}/chat/`,
        { headers: { Authorization: `Token ${token}` } },
      );
      const data = (await response.json().catch(() => ({}))) as {
        messages?: ChatMessage[];
        pendingRevisionCount?: number;
        error?: string;
      };
      if (!response.ok) {
        throw new Error(data.error || "대화 기록을 불러오지 못했습니다.");
      }
      setMessages(data.messages ?? []);
      setPendingRevisionCount(data.pendingRevisionCount ?? 0);
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "대화 기록을 불러오지 못했습니다.",
      );
    } finally {
      setIsHistoryLoading(false);
    }
  }, [bidNtceNo]);

  useEffect(() => {
    if (!embedded) document.title = `AI비서 · ${bidTitle}`;
    const timer = window.setTimeout(() => void loadHistory(), 0);
    return () => window.clearTimeout(timer);
  }, [bidTitle, embedded, loadHistory]);

  useEffect(() => {
    const area = messageAreaRef.current;
    if (area) area.scrollTop = area.scrollHeight;
  }, [messages, isAnswerLoading, isApplying]);

  async function submitMessage(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedMessage = message.trim();
    const token = localStorage.getItem("auth_token");
    if (!trimmedMessage || !token || isAnswerLoading || isApplying) return;

    const normalizedMessage = trimmedMessage.replace(/[\s.!?]/g, "");
    if (pendingRevisionCount > 0) {
      if (/^(네|예|응|좋아|확인|진행|반영|해줘|해주세요)/.test(normalizedMessage)) {
        setMessage("");
        await applyRevisionRequests(trimmedMessage, false);
        return;
      }
      if (/^(아니|아니요|취소|하지마)/.test(normalizedMessage)) {
        setMessage("");
        await applyRevisionRequests(trimmedMessage, true);
        return;
      }
    }

    setMessage("");
    setError("");
    setIsAnswerLoading(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/bids/${bidNtceNo}/chat/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Token ${token}`,
          },
          body: JSON.stringify({
            message: trimmedMessage,
            intent: "auto",
            slide_number: selectedSlide ?? null,
          }),
        },
      );
      const data = (await response.json().catch(() => ({}))) as {
        pendingRevisionCount?: number;
        error?: string;
      };
      if (!response.ok) {
        throw new Error(data.error || "AI비서가 요청을 처리하지 못했습니다.");
      }

      setPendingRevisionCount(
        data.pendingRevisionCount ?? pendingRevisionCount,
      );
      await loadHistory();
      window.opener?.postMessage(
        { type: "bid-chat-used", bidNtceNo },
        window.location.origin,
      );
    } catch (requestError) {
      setMessage(trimmedMessage);
      setError(
        requestError instanceof Error
          ? requestError.message
          : "AI비서 사용 중 오류가 발생했습니다.",
      );
    } finally {
      setIsAnswerLoading(false);
    }
  }

  async function applyRevisionRequests(confirmation: string, cancel: boolean) {
    const token = localStorage.getItem("auth_token");
    if (!token || pendingRevisionCount === 0 || isApplying) return;

    setIsApplying(true);
    setError("");
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/bids/${bidNtceNo}/proposal/feedback/`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Token ${token}`,
          },
          body: JSON.stringify({ confirmation, cancel }),
        },
      );
      const data = (await response.json().catch(() => ({}))) as
        BidProposalResponse & { error?: string };
      if (!response.ok || !data.proposal) {
        throw new Error(data.error || "수정 요청을 반영하지 못했습니다.");
      }
      onProposalUpdated?.(data.proposal);
      await loadHistory();
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "수정 요청을 반영하지 못했습니다.",
      );
    } finally {
      setIsApplying(false);
    }
  }

  async function deleteMessage(messageId: number) {
    if (!window.confirm("이 메시지를 지우시겠습니까?")) return;
    const token = localStorage.getItem("auth_token");
    if (!token) return;

    const response = await fetch(
      `${API_BASE_URL}/api/bids/${bidNtceNo}/chat/${messageId}/`,
      {
        method: "DELETE",
        headers: { Authorization: `Token ${token}` },
      },
    );
    const data = (await response.json().catch(() => ({}))) as {
      message?: ChatMessage;
      error?: string;
    };
    if (!response.ok || !data.message) {
      setError(data.error || "메시지를 삭제하지 못했습니다.");
      return;
    }
    setMessages((current) =>
      current.map((item) =>
        item.id === messageId ? (data.message as ChatMessage) : item,
      ),
    );
    await loadHistory();
  }

  function openPopup() {
    const query = new URLSearchParams({ bid: bidNtceNo, title: bidTitle });
    const windowName = `bid-chat-${bidNtceNo.replace(/[^a-zA-Z0-9_-]/g, "")}`;
    const chatWindow = window.open(
      `/bidChat?${query.toString()}`,
      windowName,
      "popup=yes,width=540,height=760,resizable=yes,scrollbars=yes",
    );
    chatWindow?.focus();
  }

  return (
    <main
      className={
        embedded && showHeader
          ? "flex h-full min-h-[560px] flex-col bg-white"
          : embedded
            ? "flex h-full min-h-0 flex-col bg-white"
            : "flex h-screen min-h-[520px] flex-col bg-white"
      }
    >
      {showHeader && (
        <header className="flex items-start justify-between border-b border-slate-200 px-5 py-4">
          <div className="min-w-0 pr-4">
            <h1 className="text-base font-bold text-slate-950">AI비서</h1>
            <p className="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">
              {bidTitle}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {embedded && (
              <button
                className="h-8 cursor-pointer rounded-md px-2 text-xs font-semibold text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                onClick={openPopup}
                type="button"
              >
                새 창
              </button>
            )}
            {(!embedded || onClose) && (
              <button
                aria-label="AI비서 창 닫기"
                className="flex h-8 w-8 cursor-pointer items-center justify-center rounded-md text-xl text-slate-500 hover:bg-slate-100 hover:text-slate-900"
                onClick={onClose ?? (() => window.close())}
                type="button"
              >
                ×
              </button>
            )}
          </div>
        </header>
      )}

      {!showHeader && (
        <div className="flex items-center justify-between border-b border-slate-100 px-4 py-2">
          <span className="text-xs font-semibold text-slate-500">대화 기록</span>
          <button
            className="h-7 cursor-pointer rounded-md px-2 text-xs font-semibold text-slate-500 hover:bg-slate-100 hover:text-slate-900"
            onClick={openPopup}
            type="button"
          >
            새 창
          </button>
        </div>
      )}

      <div
        className="flex-1 space-y-4 overflow-y-auto bg-slate-50 px-4 py-5"
        ref={messageAreaRef}
      >
        {isHistoryLoading && (
          <p className="py-20 text-center text-sm text-slate-500">
            이전 대화를 불러오는 중입니다.
          </p>
        )}
        {!isHistoryLoading && messages.length === 0 && (
          <div className="py-16 text-center">
            <p className="text-sm text-slate-500">대화 내용이 없습니다.</p>
            <p className="mx-auto mt-3 max-w-xs text-xs leading-5 text-slate-400">
              예: 발주처가 가장 중요하게 평가하는 항목을 정리해줘.
              <br />
              예: 8페이지의 수행 전략을 더 구체적으로 수정해줘.
            </p>
          </div>
        )}

        {messages.map((item) => (
          <div
            className={
              item.role === "user"
                ? "ml-auto max-w-[88%]"
                : "mr-auto max-w-[94%]"
            }
            key={item.id}
          >
            <div
              className={`group relative whitespace-pre-wrap rounded-lg px-4 py-3 pr-8 text-sm leading-6 ${
                item.isDeleted
                  ? "border border-slate-200 bg-slate-100 italic text-slate-400"
                  : item.role === "user"
                    ? "bg-blue-600 text-white"
                    : "border border-slate-200 bg-white text-slate-800"
              }`}
            >
              {item.text}
              {!item.isDeleted && (
                <button
                  aria-label="메시지 삭제"
                  className={`absolute right-1.5 top-1.5 flex h-6 w-6 cursor-pointer items-center justify-center rounded text-sm opacity-60 hover:opacity-100 ${
                    item.role === "user"
                      ? "hover:bg-blue-500"
                      : "hover:bg-slate-100"
                  }`}
                  onClick={() => void deleteMessage(item.id)}
                  title="메시지 삭제"
                  type="button"
                >
                  ×
                </button>
              )}
            </div>
            {item.messageType === "proposal" && !item.isDeleted && (
              <p className="mt-1 px-1 text-right text-[11px] text-blue-500">
                {item.status === "pending"
                  ? "사용자 확인 대기"
                  : item.status === "failed"
                    ? "반영 실패"
                    : "제안서 반영 완료"}
              </p>
            )}
            {item.messageType === "question" &&
              Array.isArray(item.sources) &&
              item.sources.length > 0 && (
                <div className="mt-2 space-y-1 px-1">
                  {item.sources.map((source) => (
                    <p
                      className="text-xs leading-5 text-slate-500"
                      key={`${item.id}-${source.number}`}
                    >
                      출처 {source.number}. {source.file_name} · {source.location}
                    </p>
                  ))}
                </div>
              )}
          </div>
        ))}

        {(isAnswerLoading || isApplying) && (
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <span
              aria-hidden="true"
              className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-blue-600"
            />
            <p>
              {isApplying
                ? "수정 요청을 제안서에 반영하고 있습니다."
                : "AI비서가 요청을 확인하고 있습니다."}
            </p>
          </div>
        )}
      </div>

      {error && (
        <p className="border-t border-red-100 bg-red-50 px-4 py-2 text-sm text-red-600">
          {error}
        </p>
      )}

      <form
        className="border-t border-slate-200 bg-white p-4"
        onSubmit={submitMessage}
      >
        <div className="flex items-end gap-2">
          <textarea
            className="min-h-28 max-h-56 min-w-0 flex-1 resize-y rounded-md border border-slate-300 px-3 py-2 text-sm leading-6 outline-none focus:border-blue-500"
            disabled={isAnswerLoading || isApplying}
            maxLength={1000}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if (
                event.key !== "Enter" ||
                event.shiftKey ||
                event.ctrlKey ||
                event.nativeEvent.isComposing
              ) {
                return;
              }
              event.preventDefault();
              event.currentTarget.form?.requestSubmit();
            }}
            placeholder="공고 질문이나 제안서 수정 요청을 입력해 주세요."
            rows={4}
            value={message}
          />
          <button
            className="h-11 cursor-pointer rounded-md bg-blue-600 px-4 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            disabled={!message.trim() || isAnswerLoading || isApplying}
            type="submit"
          >
            보내기
          </button>
        </div>
      </form>
    </main>
  );
}
