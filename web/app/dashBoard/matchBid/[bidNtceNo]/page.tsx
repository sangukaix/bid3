import ProposalWorkspace from "@/components/proposal/ProposalWorkspace";

type PageProps = {
  params: Promise<{ bidNtceNo: string }>;
};

export default async function ProposalWorkspacePage({ params }: PageProps) {
  const { bidNtceNo } = await params;

  return <ProposalWorkspace bidNtceNo={bidNtceNo} />;
}
