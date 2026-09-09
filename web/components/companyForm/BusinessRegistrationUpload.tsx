"use client";

import { DragEvent, useRef, useState } from "react";

import { API_BASE_URL } from "@/lib/api";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["application/pdf", "image/jpeg", "image/png"];

export type ExtractedBusinessInfo = {
  company_name?: string | null;
  business_registration_number?: string | null;
  representative_name?: string | null;
  address?: string | null;
};

type BusinessRegistrationUploadProps = {
  onExtracted: (data: ExtractedBusinessInfo) => void;
};

export default function BusinessRegistrationUpload({ onExtracted }: BusinessRegistrationUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [message, setMessage] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  async function analyzeFile(file: File) {
    if (!ALLOWED_TYPES.includes(file.type)) {
      setMessage("PDF, JPG, PNG 파일만 사용할 수 있습니다.");
      return;
    }
    if (file.size > MAX_FILE_SIZE) {
      setMessage("파일 크기는 5MB 이하여야 합니다.");
      return;
    }

    const token = localStorage.getItem("auth_token");
    if (!token) {
      setMessage("로그인 후 사용할 수 있습니다.");
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => controller.abort(), 45_000);
    setIsAnalyzing(true);
    setMessage("사업자등록증에 적힌 정보를 확인하고 있습니다.");

    try {
      const response = await fetch(`${API_BASE_URL}/api/company-profile/business-registration/`, {
        method: "POST",
        headers: { Authorization: `Token ${token}` },
        body: formData,
        signal: controller.signal,
      });
      const contentType = response.headers.get("content-type") ?? "";
      const data = contentType.includes("application/json")
        ? (await response.json()) as ExtractedBusinessInfo & { error?: string }
        : { error: `분석 서버 요청에 실패했습니다. (${response.status})` };

      if (!response.ok) {
        setMessage(data.error ?? "사업자등록증을 읽지 못했습니다.");
        return;
      }

      onExtracted(data);
      setMessage("저장 전에 자동 입력된 내용에 오타가 없는지 확인해 주세요.");
    } catch (error) {
      setMessage(
        error instanceof DOMException && error.name === "AbortError"
          ? "분석 시간이 오래 걸려 중단했습니다. 이미지 파일로 다시 시도해 주세요."
          : "사업자등록증 분석 서버에 연결할 수 없습니다.",
      );
    } finally {
      window.clearTimeout(timeoutId);
      setIsAnalyzing(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) void analyzeFile(file);
  }

  return (
    <div className="md:col-span-3">
      <div
        className="flex min-h-32 flex-col items-center justify-center rounded-lg border border-dashed border-blue-300 bg-blue-50/60 px-5 py-6 text-center transition hover:border-blue-500 hover:bg-blue-50"
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        <p className="text-sm font-bold text-slate-800">사업자등록증 첨부</p>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          첨부 시 기본 정보가 자동으로 입력되며 더욱 정밀한 AI 분석 결과를 받아보실 수 있습니다.
        </p>
        <div
          className={`relative mt-3 overflow-hidden rounded-md border border-blue-200 bg-white px-3 py-1.5 text-xs font-normal text-blue-700 transition-colors ${
            isAnalyzing ? "cursor-wait text-slate-400" : "cursor-pointer hover:border-blue-300 hover:bg-blue-100"
          }`}
        >
          <span className="pointer-events-none">
            {isAnalyzing ? "분석 중..." : "파일 선택"}
          </span>
          <input
            aria-label="파일 선택"
            className="absolute inset-0 h-full w-full cursor-pointer opacity-0 disabled:cursor-wait"
            disabled={isAnalyzing}
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void analyzeFile(file);
            }}
            ref={fileInputRef}
            type="file"
          />
        </div>
      </div>
      {message && <p className="mt-2 text-sm text-blue-700" role="status">{message}</p>}
    </div>
  );
}
