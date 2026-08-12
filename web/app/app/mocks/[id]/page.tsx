import MockRunner from "../MockRunner";

export default async function StartMockPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <MockRunner examId={Number(id)} />;
}
