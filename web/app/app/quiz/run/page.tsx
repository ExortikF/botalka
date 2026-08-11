import { Suspense } from "react";
import QuizRunner from "./QuizRunner";
import type { QuizPreset } from "@/lib/api";

export default async function QuizRunPage({
  searchParams,
}: {
  searchParams: Promise<{
    types?: string;
    length?: string;
    preset?: string;
    subject?: string;
  }>;
}) {
  const params = await searchParams;

  const taskTypeIds = (params.types ?? "")
    .split(",")
    .map(Number)
    .filter((n) => Number.isFinite(n) && n > 0);

  const length = Number(params.length);
  const preset =
    params.preset === "weak" || params.preset === "mistakes"
      ? (params.preset as QuizPreset)
      : null;

  return (
    <Suspense fallback={<p className="muted">Загрузка…</p>}>
      <QuizRunner
        subject={params.subject ?? "math_prof"}
        taskTypeIds={taskTypeIds}
        preset={preset}
        length={Number.isFinite(length) && length > 0 ? length : 10}
      />
    </Suspense>
  );
}
