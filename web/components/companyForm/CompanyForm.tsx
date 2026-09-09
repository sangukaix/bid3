"use client";

import { FormEvent, useState } from "react";

import Input from "@/components/ui/Input"; // 한 줄 입력칸을 재사용하기 위한 컴포넌트
import RegionSelector, { parseRegions } from "@/components/ui/RegionSelector"; // 여러 희망 지역 선택
import Textarea from "@/components/ui/Textarea"; // 안내와 예시가 있는 여러 줄 입력칸
import BusinessRegistrationUpload, { type ExtractedBusinessInfo } from "@/components/companyForm/BusinessRegistrationUpload"; // 사업자등록증 기본정보 추출
import CertificationFields from "@/components/companyForm/CertificationFields"; // 면허와 인증을 항목별로 입력
import CompanyDocuments from "@/components/companyForm/CompanyDocuments"; // 회사 제안서와 소개서 업로드
import FormSection from "@/components/companyForm/FormSection"; // 관련 입력값을 주제별로 묶는 컴포넌트
import IndustrySelector from "@/components/companyForm/IndustrySelector"; // 여러 사업 분야 선택
import KeywordSelector from "@/components/companyForm/KeywordSelector"; // 희망 키워드를 태그로 입력
import PerformanceFields from "@/components/companyForm/PerformanceFields"; // 수행 실적을 항목별로 입력
import WonInput from "@/components/ui/WonInput"; // 원화 금액을 세 자리 쉼표로 표시
import { API_BASE_URL } from "@/lib/api";
import { formatCompanyKeywords, parseKeywordText } from "@/lib/companyKeywords";
import type { CompanyProfileData } from "@/types/company"; // 회사 정보 JSON의 TypeScript 자료형

const nullableFields = new Set([
  "established_date",
  "employee_count",
  "capital",
  "annual_revenue",
]); // 빈 문자열 대신 null을 보내야 하는 Django 필드

type CompanyFormProps = {
  initialProfile?: CompanyProfileData; // 수정할 때 입력칸에 채울 기존 회사 정보
  onCancel?: () => void; // 수정을 취소하고 요약 화면으로 돌아감
  onSaved?: (profile: CompanyProfileData) => void; // 저장한 정보를 요약 화면에 전달
};

export default function CompanyForm({ initialProfile, onCancel, onSaved }: CompanyFormProps) { // 회사 정보 입력 화면 전체를 담당하는 컴포넌트
  const [message, setMessage] = useState(""); // 저장 성공 또는 오류 안내문
  const [isSubmitting, setIsSubmitting] = useState(false); // 중복 저장 방지 상태
  const [basicInfo, setBasicInfo] = useState({
    company_name: initialProfile?.company_name ?? "",
    business_registration_number: initialProfile?.business_registration_number ?? "",
    representative_name: initialProfile?.representative_name ?? "",
    address: initialProfile?.address ?? "",
  }); // 사업자등록증으로 자동입력할 수 있는 기본정보
  const [preferredRegions, setPreferredRegions] = useState(() =>
    parseRegions(initialProfile?.preferred_region ?? ""),
  ); // 저장 또는 수정할 희망 지역 목록
  const [preferredKeywords, setPreferredKeywords] = useState(() =>
    parseKeywordText(formatCompanyKeywords(initialProfile)),
  ); // 저장 또는 수정할 희망 키워드 목록
  const [excludedKeywords, setExcludedKeywords] = useState(() =>
    parseKeywordText(initialProfile?.excluded_keywords ?? ""),
  ); // 추천에서 제외할 키워드 목록
  const isEditing = Boolean(initialProfile); // 기존 정보가 있으면 수정 모드
  const selectClassName = "mt-2 h-11 w-full rounded-md border border-slate-300 bg-white px-3.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100";

  function applyBusinessRegistration(data: ExtractedBusinessInfo) {
    setBasicInfo((current) => ({
      company_name: data.company_name || current.company_name,
      business_registration_number: data.business_registration_number || current.business_registration_number,
      representative_name: data.representative_name || current.representative_name,
      address: data.address || current.address,
    }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); // 브라우저의 기본 새로고침 방지
    const token = localStorage.getItem("auth_token"); // 로그인할 때 저장한 인증표

    if (!token) {
      setMessage("회사 정보를 저장하려면 먼저 로그인해 주세요.");
      return;
    }

    if (preferredKeywords.length === 0) {
      setMessage("희망 키워드를 한 개 이상 입력해 주세요.");
      return;
    }

    const formData = new FormData(event.currentTarget); // 입력값 전체를 모음
    if (!String(formData.get("industry") ?? "").trim()) {
      setMessage("사업 분야를 한 개 이상 선택해 주세요.");
      return;
    }
    const companyData: Record<string, FormDataEntryValue | null> = {};

    for (const [name, value] of formData.entries()) {
      if (value !== "") {
        companyData[name] = value;
      } else if (isEditing) {
        companyData[name] = nullableFields.has(name) ? null : ""; // 수정할 때 지운 값도 반영
      }
    }

    setMessage("");
    setIsSubmitting(true);

    try {
      const response = await fetch(`${API_BASE_URL}/api/company-profile/`, {
        method: isEditing ? "PATCH" : "POST", // 최초 저장과 기존 정보 수정을 구분
        headers: {
          Authorization: `Token ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(companyData),
      });

      if (!response.ok) {
        const errors = (await response.json()) as Record<string, string[]>;
        setMessage(Object.values(errors).flat().join(" "));
        return;
      }

      const data = (await response.json()) as { profile: CompanyProfileData };
      setMessage(isEditing ? "회사 정보가 수정되었습니다." : "회사 정보가 저장되었습니다.");
      onSaved?.(data.profile); // 저장 직후 요약 화면으로 변경
    } catch {
      setMessage("회사 정보 저장 서버에 연결할 수 없습니다.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className="mt-6 max-w-5xl space-y-5" onSubmit={handleSubmit}> {/* 여러 입력 영역과 저장 버튼을 하나의 폼으로 묶음 */}
      <FormSection columns={3} title="기본 정보" description="회사를 확인하기 위한 기본 정보를 입력해주세요.">
        <BusinessRegistrationUpload onExtracted={applyBusinessRegistration} />

        <Input label="회사명" name="company_name" onChange={(event) => setBasicInfo({ ...basicInfo, company_name: event.target.value })} placeholder="예: 비드링크" required showRequiredMark value={basicInfo.company_name} />
        <Input label="사업자등록번호" name="business_registration_number" onChange={(event) => setBasicInfo({ ...basicInfo, business_registration_number: event.target.value })} placeholder="000-00-00000" required showRequiredMark value={basicInfo.business_registration_number} />
        <Input label="대표자명" name="representative_name" onChange={(event) => setBasicInfo({ ...basicInfo, representative_name: event.target.value })} placeholder="예: 김대표" required showRequiredMark value={basicInfo.representative_name} />
        <Input defaultValue={initialProfile?.phone} label="전화번호" name="phone" type="tel" placeholder="02-1234-5678" />
        <Input defaultValue={initialProfile?.email} label="이메일" name="email" type="email" placeholder="contact@company.com" />
        <Input defaultValue={initialProfile?.established_date ?? ""} label="설립일" name="established_date" type="date" />

        <Input defaultValue={initialProfile?.website_url_1} label="회사 홈페이지 1" name="website_url_1" type="url" placeholder="https://company.com" />
        <Input defaultValue={initialProfile?.website_url_2} label="회사 홈페이지 2" name="website_url_2" type="url" placeholder="https://brand.company.com" />

        <div className="md:col-span-3"> {/* 주소 입력칸은 세 열 전체를 사용 */}
          <Input label="회사 소재지" name="address" onChange={(event) => setBasicInfo({ ...basicInfo, address: event.target.value })} placeholder="예: 서울특별시 강남구 테헤란로 123" required showRequiredMark value={basicInfo.address} />
        </div>
      </FormSection>

      <FormSection title="사업 정보" description="회사가 주로 수행하는 업무와 보유 역량을 입력해주세요.">
        <IndustrySelector
          initialIndustry={initialProfile?.industry}
          initialRelatedIndustries={initialProfile?.related_industries}
        />

        <div className="grid gap-4 md:col-span-2 md:grid-cols-4">
          <label className="block"> {/* 입찰 참가 제한 확인에 사용할 회사 규모 구분 */}
            <span className="text-sm font-semibold text-slate-800">회사 구분</span>
            <select className={selectClassName} defaultValue={initialProfile?.company_type ?? ""} name="company_type">
              <option value="">선택</option>
              <option value="small-medium">중소기업</option>
              <option value="small">소기업</option>
              <option value="micro">소상공인</option>
              <option value="other">기타</option>
            </select>
          </label>

          <Input defaultValue={initialProfile?.employee_count ?? ""} label="직원 수" name="employee_count" type="number" placeholder="예: 10" />
          <WonInput defaultValue={initialProfile?.capital} label="자본금" name="capital" placeholder="예: 100,000,000" />
          <WonInput defaultValue={initialProfile?.annual_revenue} label="연 매출액" name="annual_revenue" placeholder="예: 500,000,000" />
        </div>

        <Textarea
          defaultValue={initialProfile?.main_business}
          description="회사가 제공하는 제품이나 서비스를 한 줄에 하나씩 적어주세요."
          example={"[교육] 기업·공공기관 임직원 1:1 화상영어 교육 운영\n[교육] 원어민 강사 배정·출결·학습 성과 관리\n[건설] 공공시설 건축·리모델링 및 시설물 유지보수\n[IT] 정보시스템 구축·운영 및 유지보수"}
          label="주요 사업 내용"
          name="main_business"
          placeholder="주요 사업 내용을 입력해 주세요."
          required
          rows={4}
        />

        <Textarea
          defaultValue={initialProfile?.capabilities}
          description="보유 기술, 장비, 전문 분야와 실제 수행 가능한 업무를 적어주세요."
          example={"[교육] 북미 원어민 강사 및 교육 운영 전담인력 보유\n[교육] LMS 기반 출결·수업·성과 리포트 제공\n[건설] 현장 안전관리 전담인력 및 시공 장비 보유\n[IT] 공공기관 시스템 구축·클라우드 운영 경험"}
          label="보유 기술 및 역량"
          name="capabilities"
          placeholder="보유 기술과 역량을 입력해 주세요."
          rows={4}
        />

        <CertificationFields initialValue={initialProfile?.licenses} />
        <PerformanceFields initialValue={initialProfile?.past_performance} />
      </FormSection>

      {isEditing && <CompanyDocuments editable />}

      <FormSection title="희망 입찰 조건" description="찾고 싶은 입찰공고의 기준을 입력해주세요.">
        <div className="md:col-span-2">
          <KeywordSelector
            keywords={preferredKeywords}
            name="preferred_keywords"
            onChange={setPreferredKeywords}
          />
          <input name="required_keywords" readOnly type="hidden" value="" />
        </div>

        <div className="md:col-span-2">
          <RegionSelector
            description="선택한 모든 지역과 지역 제한이 없는 공고를 추천합니다."
            name="preferred_region"
            onChange={setPreferredRegions}
            regions={preferredRegions}
          />
        </div>

        <div className="md:col-span-2 md:max-w-sm">
          <label className="block">
            <span className="text-sm font-semibold text-slate-800">공고 유형</span>
            <select className={selectClassName} defaultValue={initialProfile?.preferred_bid_type ?? ""} name="preferred_bid_type">
              <option value="">전체</option>
              <option value="service">용역</option>
              <option value="goods">물품</option>
              <option value="construction">공사</option>
            </select>
          </label>
        </div>

        <div className="md:col-span-2">
          <KeywordSelector
            description="공고에 포함되면 추천에서 제외할 단어를 하나씩 추가하세요. 없다면 비워두세요."
            keywords={excludedKeywords}
            label="제외 키워드"
            name="excluded_keywords"
            onChange={setExcludedKeywords}
            required={false}
            tone="red"
          />
        </div>
      </FormSection>

      {message && (
        <p className="rounded-md bg-slate-100 px-4 py-3 text-sm text-slate-700" role="status">
          {message}
        </p>
      )}

      <div className="sticky bottom-4 z-10 flex items-center justify-end gap-2 rounded-lg border border-slate-200 bg-white/95 p-3 shadow-sm backdrop-blur"> {/* 긴 양식에서도 저장 버튼을 바로 사용할 수 있는 영역 */}
        {isEditing && (
          <button
            className="rounded-md border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
            onClick={onCancel}
            type="button"
          >
            취소
          </button>
        )}

        <button
          className="rounded-md bg-blue-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:bg-slate-300"
          disabled={isSubmitting}
          type="submit"
        >
          {isSubmitting ? "저장 중..." : isEditing ? "수정 저장" : "회사 정보 저장"}
        </button>
      </div>
    </form>
  );
}
