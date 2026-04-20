import { formatDistanceToNow } from "date-fns";
import { AlertCircle, CheckCircle2, Clock } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CheckResult } from "@/types/status";

interface EndpointCardProps {
  endpoint: CheckResult;
}

export function EndpointCard({ endpoint }: EndpointCardProps) {
  const isUp = endpoint.status === "up";
  const lastChecked = formatDistanceToNow(new Date(endpoint.timestamp), {
    addSuffix: true,
  });

  return (
    <Card
      className={
        isUp
          ? "border-l-4 border-l-emerald-500"
          : "border-l-4 border-l-rose-500"
      }
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="truncate text-base font-semibold">
            {endpoint.endpoint_name}
          </CardTitle>
          <Badge
            variant={isUp ? "default" : "destructive"}
            className={
              isUp
                ? "bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/20 dark:text-emerald-400"
                : undefined
            }
          >
            {isUp ? (
              <CheckCircle2 className="mr-1 h-3 w-3" />
            ) : (
              <AlertCircle className="mr-1 h-3 w-3" />
            )}
            {endpoint.status.toUpperCase()}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-2 text-sm">
        <p className="text-muted-foreground truncate" title={endpoint.url}>
          {endpoint.url}
        </p>

        <div className="text-muted-foreground flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
          {endpoint.response_time_ms !== null && (
            <span className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {Math.round(endpoint.response_time_ms)}ms
            </span>
          )}
          {endpoint.http_status !== null && (
            <span>HTTP {endpoint.http_status}</span>
          )}
          <span>Checked {lastChecked}</span>
        </div>

        {endpoint.error && (
          <p className="bg-destructive/10 text-destructive rounded-md px-2 py-1 text-xs">
            {endpoint.error}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
