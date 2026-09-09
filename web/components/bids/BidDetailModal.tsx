import type { BidNotice } from "@/types/bid";


type BidDetailModalProps = {
  bid: BidNotice;
  flowTrigger?: boolean;
  trigger?: string;
  triggerClassName?: string;
};

type Field = readonly [keyof BidNotice, string];

type FieldGroup = {
  title: string;
  fields: Field[];
};

const FIELD_GROUPS: FieldGroup[] = [
  {
    title: "공고 기본정보",
    fields: [
      ["bidNtceNo", "공고번호"], ["bidNtceOrd", "공고차수"],
      ["refNtceNo", "참조공고번호"], ["refNtceOrd", "참조공고차수"],
      ["bidNtceNm", "공고명"], ["bidNtceSttusNm", "공고상태"],
      ["bidNtceDate", "공고일"], ["bidNtceBgn", "공고 시작일시"],
      ["ppsNtceYn", "조달청 공고 여부"], ["bsnsDivNm", "업무 구분"],
      ["dataBssDate", "데이터 기준일"],
    ],
  },
  {
    title: "입찰 및 계약방식",
    fields: [
      ["elctrnBidYn", "전자입찰 여부"], ["intrntnlBidYn", "국제입찰 여부"],
      ["cmmnCntrctYn", "공동계약 여부"], ["cmmnReciptMethdNm", "공동수급 접수방법"],
      ["cntrctCnclsSttusNm", "계약체결 상태"], ["cntrctCnclsMthdNm", "계약 방법"],
      ["bidwinrDcsnMthdNm", "낙찰자 결정방법"],
    ],
  },
  {
    title: "공고기관",
    fields: [
      ["ntceInsttNm", "공고기관명"], ["ntceInsttCd", "공고기관 코드"],
      ["ntceInsttOfclDeptNm", "담당부서"], ["ntceInsttOfclNm", "담당자"],
      ["ntceInsttOfclTel", "전화번호"], ["ntceInsttOfclEmailAdrs", "이메일"],
    ],
  },
  {
    title: "수요기관",
    fields: [
      ["dmndInsttNm", "수요기관명"], ["dmndInsttCd", "수요기관 코드"],
      ["dmndInsttOfclDeptNm", "담당부서"], ["dmndInsttOfclNm", "담당자"],
      ["dmndInsttOfclTel", "전화번호"], ["dmndInsttOfclEmailAdrs", "이메일"],
    ],
  },
  {
    title: "입찰 일정",
    fields: [
      ["bidBeginDate", "입찰 시작일"], ["bidBeginTm", "입찰 시작시간"],
      ["bidClseDate", "입찰 마감일"], ["bidClseTm", "입찰 마감시간"],
      ["opengDate", "개찰일"], ["opengTm", "개찰시간"],
      ["opengPlce", "개찰장소"],
      ["bidPrtcptQlfctRgstClseDate", "참가자격 등록 마감일"],
      ["bidPrtcptQlfctRgstClseTm", "참가자격 등록 마감시간"],
      ["cmmnReciptAgrmntClseDate", "공동수급 협정 마감일"],
      ["cmmnReciptAgrmntClseTm", "공동수급 협정 마감시간"],
    ],
  },
  {
    title: "설명회",
    fields: [
      ["presnatnOprtnYn", "설명회 실시 여부"], ["presnatnOprtnDate", "설명회 날짜"],
      ["presnatnOprtnTm", "설명회 시간"], ["presnatnOprtnPlce", "설명회 장소"],
    ],
  },
  {
    title: "금액 및 예정가격",
    fields: [
      ["asignBdgtAmt", "배정예산"], ["presmptPrce", "추정가격"],
      ["rsrvtnPrceDcsnMthdNm", "예정가격 결정방법"],
    ],
  },
  {
    title: "참가 제한",
    fields: [
      ["rgnLmtYn", "지역 제한 여부"], ["prtcptPsblRgnNm", "참가 가능지역"],
      ["indstrytyLmtYn", "업종 제한 여부"], ["bidprcPsblIndstrytyNm", "참가 가능업종"],
    ],
  },
  {
    title: "원문",
    fields: [["bidNtceUrl", "나라장터 공고 URL"]],
  },
];

const AMOUNT_FIELDS = new Set(["asignBdgtAmt", "presmptPrce"]);


function formatValue(key: keyof BidNotice, value: BidNotice[keyof BidNotice]) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  if (AMOUNT_FIELDS.has(String(key))) {
    const amount = Number(value);
    return Number.isFinite(amount) ? `${amount.toLocaleString("ko-KR")}원` : value;
  }

  return value;
}


export default function BidDetailModal({
  bid,
  flowTrigger = false,
  trigger = "전체보기",
  triggerClassName = "whitespace-nowrap rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700 transition-colors hover:border-blue-500 hover:text-blue-600",
}: BidDetailModalProps) {
  const dialogId = `bid-detail-${bid.bidNtceNo}-${bid.bidNtceOrd}`;

  return (
    <>
      {flowTrigger ? (
        <button className="contents" popoverTarget={dialogId} type="button">
          <span className={triggerClassName}>{trigger}</span>
        </button>
      ) : (
        <button
          className={triggerClassName}
          popoverTarget={dialogId}
          type="button"
        >
          {trigger}
        </button>
      )}

      <div
        aria-labelledby={`${dialogId}-title`}
        className="fixed inset-0 m-auto max-h-[calc(100vh-3rem)] w-[min(960px,calc(100vw-2rem))] overflow-hidden rounded-lg border-0 bg-white p-0 shadow-2xl backdrop:bg-slate-950/55"
        id={dialogId}
        popover="auto"
        role="dialog"
      >
          <div className="flex max-h-[calc(100vh-3rem)] flex-col overflow-hidden">
            <header className="flex items-start justify-between gap-6 border-b border-slate-200 bg-white px-6 py-5 text-left">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-blue-600">
                  {bid.bidNtceNo} · {bid.bidNtceOrd}차
                </p>
                <h2
                  className="mt-1 break-words text-lg font-bold leading-7 text-slate-950"
                  id={`${dialogId}-title`}
                >
                  {bid.bidNtceNm}
                </h2>
              </div>

              <button
                aria-label="상세정보 닫기"
                className="h-9 w-9 shrink-0 text-2xl leading-none text-slate-500 hover:text-slate-950"
                popoverTarget={dialogId}
                popoverTargetAction="hide"
                type="button"
              >
                ×
              </button>
            </header>

            <div className="overflow-y-auto px-6 py-2 text-left">
              {FIELD_GROUPS.map((group) => (
                <section className="border-b border-slate-200 py-5 last:border-b-0" key={group.title}>
                  <h3 className="mb-3 text-sm font-bold text-slate-950">{group.title}</h3>
                  <dl className="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
                    {group.fields.map(([key, label]) => (
                      <div className="grid grid-cols-[140px_minmax(0,1fr)] gap-3 border-t border-slate-100 py-2.5" key={String(key)}>
                        <dt className="text-xs font-semibold text-slate-500">{label}</dt>
                        <dd className="break-words text-sm text-slate-800">
                          {key === "bidNtceUrl" && typeof bid[key] === "string" ? (
                            <a
                              className="font-semibold text-blue-600 underline-offset-4 hover:underline"
                              href={bid[key] as string}
                              rel="noreferrer"
                              target="_blank"
                            >
                              나라장터 원문 열기
                            </a>
                          ) : (
                            formatValue(key, bid[key])
                          )}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </section>
              ))}
            </div>
          </div>
        </div>
    </>
  );
}
