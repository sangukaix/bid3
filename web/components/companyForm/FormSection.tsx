type FormSectionProps = { // FormSection 컴포넌트가 받을 값들의 타입
  title: string; // 각 입력 영역의 제목
  description: string; // 제목 아래에 보이는 짧은 설명
  children: React.ReactNode; // 영역 안에 들어갈 입력 요소들
  columns?: 2 | 3; // PC 화면에서 사용할 입력 열 개수
};

export default function FormSection({ title, description, children, columns = 2 }: FormSectionProps) {
  return (
    <section className="app-panel overflow-hidden rounded-lg border"> {/* 하나의 입력 주제를 묶는 영역 */}
      <div className="app-panel-soft flex items-start gap-3 border-b px-6 py-5"> {/* 영역 제목과 입력칸을 시각적으로 구분 */}
        <span aria-hidden="true" className="mt-1 h-8 w-1 rounded-full bg-blue-600" />
        <div>
          <h2 className="text-base font-bold text-slate-950">{title}</h2>
          <p className="mt-1 text-sm leading-5 text-slate-500">{description}</p>
        </div>
      </div>

      <div className={`grid gap-x-5 gap-y-6 p-6 ${columns === 3 ? "md:grid-cols-3" : "md:grid-cols-2"}`}> {/* PC에서는 지정한 열 수로 배치 */}
        {children} {/* CompanyForm에서 전달한 입력 요소가 표시되는 자리 */}
      </div>
    </section>
  );
}
