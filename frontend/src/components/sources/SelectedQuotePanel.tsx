import { useState } from "react";
import { locateInVersion } from "../../api/workbench";
import { workbenchFailureMessage } from "../messages";

export interface TextSelection {
  start: number;
  end: number;
  quote: string;
}

type VerifyState =
  | { status: "idle" }
  | { status: "checking" }
  | { status: "ok" }
  | { status: "error"; message: string };

interface SelectedQuotePanelProps {
  versionId: string;
  selection: TextSelection;
  onBind: () => void;
}

/** The pending citation from a selection: verify against the version, then bind. */
export function SelectedQuotePanel({ versionId, selection, onBind }: SelectedQuotePanelProps) {
  const [verify, setVerify] = useState<VerifyState>({ status: "idle" });

  const handleVerify = (): void => {
    setVerify({ status: "checking" });
    locateInVersion(versionId, {
      start: selection.start,
      end: selection.end,
      exact_quote: selection.quote,
    })
      .then(() => setVerify({ status: "ok" }))
      .catch((error: unknown) =>
        setVerify({ status: "error", message: workbenchFailureMessage(error) }),
      );
  };

  return (
    <div data-testid="selected-quote">
      <p>
        已选引文：区间 [{selection.start}, {selection.end})，共 {selection.end - selection.start} 个
        Unicode 码点。
      </p>
      <blockquote>{selection.quote}</blockquote>
      {verify.status === "checking" ? (
        <p role="status">正在校验…</p>
      ) : verify.status === "ok" ? (
        <p role="status" data-testid="verify-ok">
          校验通过：位置与字句和该版本一致。
        </p>
      ) : verify.status === "error" ? (
        <p role="alert" data-testid="verify-error">
          {verify.message}
        </p>
      ) : null}
      <button type="button" onClick={handleVerify} disabled={verify.status === "checking"}>
        校验位置
      </button>
      <button type="button" onClick={onBind} disabled={verify.status !== "ok"}>
        用于绑定证据
      </button>
    </div>
  );
}
