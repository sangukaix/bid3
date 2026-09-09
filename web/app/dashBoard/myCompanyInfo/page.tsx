import CompanyProfile from "@/components/companyForm/CompanyProfile"; // 회사 정보 조회와 요약 컴포넌트

import PageHeader from "@/components/layout/PageHeader";

export default function MyCompanyInfoPage() { // /dashBoard/myCompanyInfo 주소에서 보이는 회사 정보 페이지
  return (
    <section className="min-w-0"> {/* 다른 대시보드 페이지와 같은 본문 너비 사용 */}
      <PageHeader
        note={<p><span className="font-semibold text-red-500">*</span> 표시는 필수입니다.</p>}
        title="회사정보"
      /> {/* 페이지 제목과 필수 입력 안내 */}

      <CompanyProfile /> {/* 저장 정보가 있으면 요약, 없으면 입력 폼 표시 */}
    </section>
  );
}
