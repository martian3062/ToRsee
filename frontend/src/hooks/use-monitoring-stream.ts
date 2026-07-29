"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { apiUrl } from "@/lib/api";
import { monitoringKeys } from "@/lib/query-keys";

export type StreamStatus = "connecting" | "live" | "reconnecting";

export function useMonitoringStream(): StreamStatus {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<StreamStatus>("connecting");

  useEffect(() => {
    const source = new EventSource(apiUrl("/osint/events/stream/"));

    source.onopen = () => setStatus("live");
    source.onerror = () => setStatus("reconnecting");
    source.addEventListener("monitoring", () => {
      setStatus("live");
      void queryClient.invalidateQueries({ queryKey: monitoringKeys.all });
    });

    return () => source.close();
  }, [queryClient]);

  return status;
}
