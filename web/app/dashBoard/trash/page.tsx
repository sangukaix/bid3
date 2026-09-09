import ProposalTrash from "@/components/proposal/ProposalTrash";

import PageHeader from "@/components/layout/PageHeader";

export default function ProposalTrashPage() {
  return (
    <section className="min-w-0">
      <PageHeader description="보관한 프로젝트를 복원하거나 영구 삭제합니다." title="휴지통" />
      <ProposalTrash />
    </section>
  );
}
