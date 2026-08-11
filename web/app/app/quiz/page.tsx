import { Suspense } from "react";
import QuizRunner from "./QuizRunner";

export default async function QuizPage({
  searchParams,
}: {
  searchParams: Promise<{ type?: string; length?: string }>;
}) {
  const params = await searchParams;
  const taskType = params.type ? Number(params.type) : undefined;
  const length = params.length ? Number(params.length) : 10;

  return (
    <Suspense fallback={<p className="muted">Загрузка…</p>}>
      <QuizRunner taskType={Number.isFinite(taskType) ? taskType : undefined} length={length} />
    </Suspense>
  );
}
