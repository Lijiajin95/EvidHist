export interface FormFeedback {
  kind: "error" | "ok";
  text: string;
}

/** Shared form feedback: errors alert, successes are polite status. */
export function FormFeedback({ feedback, testId }: { feedback: FormFeedback; testId: string }) {
  return (
    <p role={feedback.kind === "error" ? "alert" : "status"} data-testid={testId}>
      {feedback.text}
    </p>
  );
}
