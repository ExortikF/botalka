import { Suspense } from "react";
import QuizRunner from "./QuizRunner";
import type { QuizPreset } from "@/lib/api";

export default async function QuizRunPage({
  searchParams,
}: {
  searchParams: Promise<{
    types?: string;
    selection?: string;
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

  // формат "1:2,6:3" — из каждой темы взять указанное число задач
  const selection = (params.selection ?? "")
    .split(",")
    .map((pair) => pair.split(":").map(Number))
    .filter(([id, count]) => Number.isFinite(id) && Number.isFinite(count) && id > 0 && count > 0)
    .map(([task_type_id, count]) => ({ task_type_id, count }));

  const length = Number(params.length);
  const PRESETS: QuizPreset[] = ["weak", "mistakes", "unsolved"];
  const preset = PRESETS.includes(params.preset as QuizPreset)
    ? (params.preset as QuizPreset)
    : null;

  return (
    <Suspense fallback={<p className="muted">Загрузка…</p>}>
      <QuizRunner
        subject={params.subject ?? "math_prof"}
        taskTypeIds={taskTypeIds}
        selection={selection}
        preset={preset}
        length={Number.isFinite(length) && length > 0 ? length : 10}
      />
    </Suspense>
  );
}
