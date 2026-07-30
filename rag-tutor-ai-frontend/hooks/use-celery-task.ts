"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { CeleryTaskStatus } from "@/lib/api/ingestion";

export type CeleryTaskPhase =
  | "idle"
  | "queued"
  | "running"
  | "success"
  | "failure";

type UseCeleryTaskOptions<TResult> = {
  fetchStatus: (taskId: string) => Promise<CeleryTaskStatus<TResult>>;
  intervalMs?: number;
  maxAttempts?: number;
  queuedMessage?: string;
  runningMessage?: string;
  onSuccess?: (status: CeleryTaskStatus<TResult>) => void;
  onFailure?: (error: Error, status?: CeleryTaskStatus<TResult>) => void;
};

function messageForState<TResult>(
  status: CeleryTaskStatus<TResult>,
  queuedMessage: string,
  runningMessage: string,
) {
  if (status.meta?.message) {
    return status.meta.message;
  }

  if (status.state === "STARTED") {
    return runningMessage;
  }

  if (status.state === "PENDING") {
    return queuedMessage;
  }

  if (status.state === "SUCCESS") {
    return "Task completed";
  }

  if (status.state === "FAILURE") {
    return status.error ?? "Task failed";
  }

  return runningMessage;
}

export function useCeleryTask<TResult>({
  fetchStatus,
  intervalMs = 3000,
  maxAttempts = 600,
  queuedMessage = "Task queued",
  runningMessage = "Task running",
  onSuccess,
  onFailure,
}: UseCeleryTaskOptions<TResult>) {
  const [taskId, setTaskId] = useState<string | null>(null);
  const [phase, setPhase] = useState<CeleryTaskPhase>("idle");
  const [state, setState] = useState<string | null>(null);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<TResult | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const onSuccessRef = useRef(onSuccess);
  const onFailureRef = useRef(onFailure);

  useEffect(() => {
    onSuccessRef.current = onSuccess;
  }, [onSuccess]);

  useEffect(() => {
    onFailureRef.current = onFailure;
  }, [onFailure]);

  const reset = useCallback(() => {
    setTaskId(null);
    setPhase("idle");
    setState(null);
    setMessage("");
    setResult(null);
    setError(null);
  }, []);

  const startPolling = useCallback(
    (nextTaskId: string, nextMessage = queuedMessage) => {
      setTaskId(nextTaskId);
      setPhase("queued");
      setState("PENDING");
      setMessage(nextMessage);
      setResult(null);
      setError(null);
    },
    [queuedMessage],
  );

  useEffect(() => {
    if (!taskId || phase === "idle" || phase === "success" || phase === "failure") {
      return;
    }

    const activeTaskId = taskId;
    let isCancelled = false;
    let timeoutId: number | null = null;
    let attempts = 0;

    async function poll() {
      attempts += 1;

      try {
        const status = await fetchStatus(activeTaskId);

        if (isCancelled) {
          return;
        }

        setState(status.state);
        setMessage(messageForState(status, queuedMessage, runningMessage));

        if (status.state === "SUCCESS") {
          setPhase("success");
          setResult(status.result ?? null);
          onSuccessRef.current?.(status);
          return;
        }

        if (status.state === "FAILURE") {
          const taskError = new Error(status.error ?? "Task failed");
          setPhase("failure");
          setError(taskError);
          onFailureRef.current?.(taskError, status);
          return;
        }

        if (attempts >= maxAttempts) {
          const timeoutError = new Error("Task status polling timed out");
          setPhase("failure");
          setError(timeoutError);
          onFailureRef.current?.(timeoutError, status);
          return;
        }

        setPhase(status.state === "STARTED" ? "running" : "queued");
        timeoutId = window.setTimeout(poll, intervalMs);
      } catch (caughtError) {
        if (isCancelled) {
          return;
        }

        const taskError =
          caughtError instanceof Error
            ? caughtError
            : new Error("Task status polling failed");

        setPhase("failure");
        setError(taskError);
        setMessage(taskError.message);
        onFailureRef.current?.(taskError);
      }
    }

    void poll();

    return () => {
      isCancelled = true;

      if (timeoutId) {
        window.clearTimeout(timeoutId);
      }
    };
  }, [
    fetchStatus,
    intervalMs,
    maxAttempts,
    phase,
    queuedMessage,
    runningMessage,
    taskId,
  ]);

  return {
    taskId,
    phase,
    state,
    message,
    result,
    error,
    isActive: phase === "queued" || phase === "running",
    startPolling,
    reset,
  };
}
