import { useCallback, useRef, useState } from "react";
import { locateQuote } from "../api/locateQuote";
import type { LocateRequest } from "../domain/locateContract";
import {
  beginTask,
  rejectTask,
  resetTask,
  resolveTask,
  type LocateTaskState,
} from "../domain/locateTask";
import { LocateForm } from "./LocateForm";
import { TaskStatus } from "./TaskStatus";

/**
 * The explicit-text citation locate tool: it validates positions and wording
 * against text the user pastes directly. It is a tool view; it is not the
 * authoritative workbench flow (which reads persisted versions by ID).
 */
export function ToolView() {
  const [task, setTask] = useState<LocateTaskState>({ status: "idle" });
  const controller = useRef<AbortController | null>(null);

  const handleSubmit = useCallback((request: LocateRequest): void => {
    controller.current?.abort();
    controller.current = new AbortController();
    const signal = controller.current.signal;
    setTask((previous) => beginTask(previous, request));
    locateQuote(request, signal)
      .then((location) => setTask((previous) => resolveTask(previous, request, location)))
      .catch((error: unknown) => setTask((previous) => rejectTask(previous, request, error)));
  }, []);

  const handleCancel = useCallback(() => {
    controller.current?.abort();
    setTask(resetTask);
  }, []);

  return (
    <section aria-labelledby="tool-heading">
      <h2 id="tool-heading">引用定位工具</h2>
      <p>本工具校验显式提供文本中的位置与字句；它不判断来源真实性，也不代表史实已经证实。</p>
      <LocateForm
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        loading={task.status === "loading"}
      />
      <TaskStatus state={task} />
    </section>
  );
}
