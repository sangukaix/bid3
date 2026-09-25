import StudioProject from "@/features/presentation-studio/StudioProject";
export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <StudioProject id={id} />;
}
