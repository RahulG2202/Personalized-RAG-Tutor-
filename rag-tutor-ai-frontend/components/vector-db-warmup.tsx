"use client";

import { useEffect, useRef } from "react";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function VectorDbWarmup() {
  const hasRequestedWarmup = useRef(false);

  useEffect(() => {
    if (hasRequestedWarmup.current) {
      return;
    }

    hasRequestedWarmup.current = true;

    fetch(`${API_BASE_URL}/api/v1/ingest/warmup`, {
      method: "POST",
      cache: "no-store",
    }).catch(() => undefined);
  }, []);

  return null;
}
