"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { sessions as sessionsApi, type ReportResponse } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import DecisionReportComponent from "@/components/DecisionReport";
import { ArrowLeft } from "lucide-react";

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { token } = useAuthStore();
  const sessionId = params.session_id as string;

  const [report, setReport] = useState<ReportResponse | null>(null);
  const [evalError, setEvalError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) router.push("/recruiter/login");
  }, [token, router]);

  // Poll evaluation status every 3 seconds until all_complete
  const { data: statusData } = useQuery({
    queryKey: ["eval-status", sessionId],
    queryFn: () => sessionsApi.evaluationStatus(sessionId),
    enabled: !!token && !!sessionId && !report,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.all_complete) return false;
      return 3000;
    },
  });

  const evaluateMutation = useMutation({
    mutationFn: async () => {
      const result = await sessionsApi.evaluate(sessionId);
      return result;
    },
    onSuccess: (data) => {
      setReport(data);
      setEvalError(null);
    },
    onError: (err: Error) => setEvalError(err.message),
  });

  if (!token) return null;

  const total = statusData?.total_answers ?? 0;
  const evaluated = statusData?.evaluated ?? 0;
  const allComplete = statusData?.all_complete ?? false;
  const progressPct = total > 0 ? (evaluated / total) * 100 : 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center gap-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => router.push("/recruiter/dashboard")}
        >
          <ArrowLeft className="w-4 h-4 mr-1" /> Dashboard
        </Button>
        <h1 className="text-base font-semibold text-gray-900">
          Session Review
        </h1>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        <div>
          <p className="text-xs text-gray-400 font-mono break-all">
            Session ID: {sessionId}
          </p>
        </div>

        {/* Evaluation Status Card */}
        {!report && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Evaluation Progress</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {total === 0 ? (
                <p className="text-sm text-gray-500">
                  Waiting for candidate to complete the interview…
                </p>
              ) : (
                <>
                  <div className="flex items-center justify-between text-sm text-gray-600">
                    <span>
                      {evaluated} of {total} answers evaluated
                    </span>
                    {allComplete && (
                      <span className="text-green-600 font-medium">
                        All complete ✓
                      </span>
                    )}
                  </div>
                  <Progress value={progressPct} className="h-2" />

                  {!allComplete && (
                    <p className="text-xs text-gray-400">
                      Evaluating answers in the background — this page auto-refreshes.
                    </p>
                  )}
                </>
              )}

              {allComplete && (
                <div className="pt-2">
                  <Button
                    onClick={() => evaluateMutation.mutate()}
                    disabled={evaluateMutation.isPending}
                    className="w-full sm:w-auto"
                  >
                    {evaluateMutation.isPending
                      ? "Generating Decision…"
                      : "Get Decision"}
                  </Button>
                  {evalError && (
                    <p className="mt-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded-md">
                      {evalError}
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Decision Report */}
        {report && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">
                Hiring Decision
              </h2>
              <Button
                variant="outline"
                size="sm"
                onClick={() => evaluateMutation.mutate()}
                disabled={evaluateMutation.isPending}
              >
                {evaluateMutation.isPending ? "Refreshing…" : "Re-run"}
              </Button>
            </div>
            <DecisionReportComponent data={report} />
          </div>
        )}
      </main>
    </div>
  );
}
