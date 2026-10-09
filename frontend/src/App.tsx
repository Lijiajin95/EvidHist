import { useCallback, useRef, useState } from "react";
import { locateQuote } from "./api/locateQuote";
import type { LocateRequest } from "./domain/locateContract";
import {
  beginTask,
  rejectTask,
  resetTask,
  resolveTask,
  type LocateTaskState,
} from "./domain/locateTask";
import { LocateForm } from "./components/LocateForm";
import { TaskStatus } from "./components/TaskStatus";

/**
 * First EvidHist screen: check a citation's position and wording against an
 * explicitly provided text version. This validates the provided text only; it
 * is not a statement about source authenticity or historical fact.
 */
export function App() {
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
    <main className="app">
      <h1>EvidHist 引文定位</h1>
      <p>本界面校验显式提供文本中的位置与字句；它不判断来源真实性，也不代表史实已经证实。</p>
      <LocateForm
        onSubmit={handleSubmit}
        onCancel={handleCancel}
        loading={task.status === "loading"}
      />
      <TaskStatus state={task} />
    </main>
  );
}
