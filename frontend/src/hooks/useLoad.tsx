import { useEffect, useState } from "react";
import { workbenchFailureMessage } from "../components/messages";

export type LoadState<T> =
  { status: "loading" } | { status: "error"; message: string } | { status: "ok"; data: T };

/**
 * Load a resource on mount (and whenever the caller's dependencies change),
 * tracking loading / error / ok so views never render partial data. Errors
 * carry the readable failure message (network, contract or 404 codes). While
 * a reload is in flight the previous data stays visible. Callers pass the
 * dependency list explicitly; the loader itself is intentionally not a
 * dependency to avoid refetch loops from per-render closures.
 */
export function useLoad<T>(load: () => Promise<T>, deps: readonly unknown[]): LoadState<T> {
  const [state, setState] = useState<LoadState<T>>({ status: "loading" });

  useEffect(() => {
    let active = true;
    load()
      .then((data) => {
        if (active) {
          setState({ status: "ok", data });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          setState({ status: "error", message: workbenchFailureMessage(error) });
        }
      });
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- deps are caller-supplied
  }, deps);

  return state;
}

/** Shared loading / failure display; the parent renders data or empty state. */
export function LoadStateView({ state }: { state: LoadState<unknown> }) {
  if (state.status === "loading") {
    return (
      <p role="status" aria-live="polite">
        正在加载…
      </p>
    );
  }
  if (state.status === "error") {
    return (
      <p role="alert" data-testid="load-error">
        {state.message}
      </p>
    );
  }
  return null;
}
