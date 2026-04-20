"use client";

import { formatDistanceToNow } from "date-fns";
import { Activity, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";

import { EndpointCard } from "@/components/EndpointCard";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchStatus } from "@/lib/api";
import type { StatusResponse } from "@/types/status";

const REFRESH_INTERVAL_MS = 10_000;

export default function DashboardPage() {
  const [data, setData] = useState<StatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setIsRefreshing(true);
      try {
        const result = await fetchStatus(controller.signal);
        setData(result);
        setError(null);
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          setError(err.message);
        }
      } finally {
        setIsRefreshing(false);
      }
    }

    load();
    const interval = setInterval(load, REFRESH_INTERVAL_MS);

    return () => {
      controller.abort();
      clearInterval(interval);
    };
  }, []);

  const upCount = data?.endpoints.filter((e) => e.status === "up").length ?? 0;
  const downCount =
    data?.endpoints.filter((e) => e.status === "down").length ?? 0;
  const totalCount = data?.endpoints.length ?? 0;

  const uptime = data
    ? formatDistanceToNow(new Date(data.started_at), { addSuffix: false })
    : null;

  return (
    <main className="bg-background min-h-screen">
      <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="bg-primary/10 rounded-lg p-2">
              <Activity className="text-primary h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight">healthping</h1>
              <p className="text-muted-foreground text-sm">
                Live endpoint monitoring dashboard
              </p>
            </div>
          </div>

          {data && (
            <div className="text-muted-foreground flex items-center gap-2 text-xs">
              <RefreshCw
                className={`h-3 w-3 ${isRefreshing ? "animate-spin" : ""}`}
              />
              Auto-refreshes every 10s
            </div>
          )}
        </header>

        {error && (
          <div className="border-destructive/50 bg-destructive/10 text-destructive mb-6 rounded-lg border px-4 py-3 text-sm">
            <p className="font-medium">Could not reach the healthping API</p>
            <p className="mt-1 text-xs opacity-80">{error}</p>
          </div>
        )}

        {!data && !error && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <Skeleton key={i} className="h-36 w-full rounded-xl" />
            ))}
          </div>
        )}

        {data && (
          <>
            <section className="mb-8 grid grid-cols-3 gap-4">
              <StatCard label="Total" value={totalCount} />
              <StatCard
                label="Up"
                value={upCount}
                accent="text-emerald-600 dark:text-emerald-400"
              />
              <StatCard
                label="Down"
                value={downCount}
                accent="text-rose-600 dark:text-rose-400"
              />
            </section>

            {data.endpoints.length === 0 ? (
              <div className="text-muted-foreground rounded-lg border border-dashed px-6 py-12 text-center text-sm">
                No endpoints configured yet.
              </div>
            ) : (
              <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {data.endpoints.map((endpoint) => (
                  <EndpointCard
                    key={endpoint.endpoint_name}
                    endpoint={endpoint}
                  />
                ))}
              </section>
            )}

            {uptime && (
              <footer className="text-muted-foreground mt-12 text-center text-xs">
                Monitor running for {uptime}
              </footer>
            )}
          </>
        )}
      </div>
    </main>
  );
}

interface StatCardProps {
  label: string;
  value: number;
  accent?: string;
}

function StatCard({ label, value, accent }: StatCardProps) {
  return (
    <div className="bg-card rounded-lg border p-4">
      <p className="text-muted-foreground text-xs uppercase tracking-wide">
        {label}
      </p>
      <p className={`mt-1 text-2xl font-bold ${accent ?? ""}`}>{value}</p>
    </div>
  );
}
