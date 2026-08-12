import MockRunner from "../../MockRunner";

export default async function ResumeMockPage({
  params,
}: {
  params: Promise<{ attempt: string }>;
}) {
  const { attempt } = await params;
  return <MockRunner attemptId={Number(attempt)} />;
}
