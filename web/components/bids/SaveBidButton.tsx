"use client"; // 클릭 상태와 localStorage를 사용하는 클라이언트 컴포넌트

import { useState } from "react";

import { API_BASE_URL } from "@/lib/api";

type SaveBidButtonProps = {
  bidNtceNo: string; // 저장 API에 전달할 나라장터 공고번호
};

type SaveState = "idle" | "saving" | "saved" | "error";

export default function SaveBidButton({ bidNtceNo }: SaveBidButtonProps) {
  const [saveState, setSaveState] = useState<SaveState>("idle"); // 버튼의 현재 상태
  const [errorMessage, setErrorMessage] = useState("");

  async function handleSave() {
    const token = localStorage.getItem("auth_token"); // 로그인할 때 브라우저에 저장한 인증표

    if (!token) {
      setSaveState("error");
      setErrorMessage("로그인 후 공고를 저장할 수 있습니다.");
      return;
    }

    setSaveState("saving");
    setErrorMessage("");

    try {
      const response = await fetch(`${API_BASE_URL}/api/saved-bids/`, {
        method: "POST",
        headers: {
          Authorization: `Token ${token}`, // Django에 현재 로그인 사용자 전달
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ bid_ntce_no: bidNtceNo }), // 선택한 공고번호를 JSON으로 전송
      });

      if (!response.ok) {
        const contentType = response.headers.get("content-type") ?? "";
        let message = `공고 저장 요청에 실패했습니다. (${response.status})`;

        if (contentType.includes("application/json")) {
          const data = (await response.json()) as { error?: string; detail?: string };
          message = data.error || data.detail || message;
        } else if (response.status === 404) {
          message = "저장 API를 찾을 수 없습니다. Django 서버를 다시 시작해 주세요.";
        }

        throw new Error(message); // HTML 오류 페이지를 JSON으로 읽지 않도록 구분
      }

      setSaveState("saved"); // 새 저장과 이미 저장된 공고 모두 저장됨으로 표시
    } catch (error) {
      setSaveState("error");
      setErrorMessage(
        error instanceof Error ? error.message : "공고를 저장하지 못했습니다.",
      );
    }
  }

  const buttonClassName = saveState === "saved"
    ? "inline-flex min-h-11 w-14 items-center justify-center whitespace-nowrap rounded-md bg-blue-50 px-2 text-xs font-semibold text-blue-700 ring-1 ring-inset ring-blue-200"
    : "inline-flex min-h-11 w-14 cursor-pointer flex-col items-center justify-center whitespace-nowrap rounded-md bg-slate-950 px-2 text-xs font-semibold leading-4 text-white transition-colors hover:bg-blue-700 disabled:bg-slate-300";

  return (
    <div className="flex flex-col items-center gap-1">
      <button
        className={buttonClassName}
        disabled={saveState === "saving" || saveState === "saved"}
        onClick={handleSave}
        title={errorMessage || "이 공고를 내가 저장한 공고에 추가"}
        type="button"
      >
        {saveState === "idle" ? <><span>공고</span><span>저장</span></> : null}
        {saveState === "saving" ? "저장 중" : null}
        {saveState === "saved" ? "저장됨" : null}
        {saveState === "error" ? "다시 시도" : null}
      </button>

      {errorMessage && (
        <span className="max-w-28 whitespace-normal text-center text-xs text-red-600" role="alert">
          {errorMessage}
        </span>
      )}
    </div>
  );
}
