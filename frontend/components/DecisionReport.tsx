"use client";

import { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { ReportResponse } from "@/lib/api";
import { ChevronDown, ChevronUp } from "lucide-react";

const TIER_CONFIG: Record<
  string,
  { label: string; color: string; bg: string }
> = {
  strong_hire: {
    label: "Strong Hire",
    color: "text-green-800",
    bg: "bg-green-100 border-green-300",
  },
  hire: {
    label: "Hire",
    color: "text-blue-800",
    bg: "bg-blue-100 border-blue-300",
  },
  maybe: {
    label: "Maybe",
    color: "text-amber-800",
    bg: "bg-amber-100 border-amber-300",
  },
  reject: {
    label: "Reject",
    color: "text-red-800",
    bg: "bg-red-100 border-red-300",
  },
};

const DIMENSION_LABELS: Record<string, string> = {
  technical_accuracy: "Technical",
  depth_of_explanation: "Depth",
  problem_solving: "Problem Solving",
  communication_clarity: "Clarity",
  relevance: "Relevance",
  reasoning_quality: "Reasoning",
};

const FLOOR_THRESHOLDS: Record<string, number> = {
  technical_accuracy: 5.0,
  depth_of_explanation: 4.0,
  problem_solving: 4.5,
  communication_clarity: 4.0,
  relevance: 3.5,
  reasoning_quality: 3.5,
};

const HALLUCINATION_LABELS: Record<string, string> = {
  technical_falsehood: "Technical Falsehood (−0.8)",
  shallow_reasoning: "Shallow Reasoning (−0.3)",
  experience_bluff: "Experience Bluff (−0.5)",
};

interface Props {
  data: ReportResponse;
}

export default function DecisionReportComponent({ data }: Props) {
  const { report } = data;
  const tier = TIER_CONFIG[report.tier] ?? TIER_CONFIG.reject;
  const [auditOpen, setAuditOpen] = useState(false);

  const chartData = Object.entries(report.dimension_averages).map(
    ([key, value]) => ({
      name: DIMENSION_LABELS[key] ?? key,
      score: parseFloat(value.toFixed(2)),
      floor: FLOOR_THRESHOLDS[key] ?? 0,
      violated: report.floor_violations.includes(key),
    })
  );

  // Collect hallucination flags from the report (penalty is aggregate)
  const hallucinationPenalty = report.hallucination_penalty;

  return (
    <div className="space-y-6">
      {/* Tier badge + scores */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row sm:items-center gap-6">
            <div
              className={`inline-flex items-center px-5 py-3 rounded-lg border text-lg font-bold ${tier.bg} ${tier.color}`}
            >
              {tier.label}
            </div>

            <div className="grid grid-cols-3 gap-4 flex-1">
              <div className="text-center">
                <p className="text-3xl font-bold text-gray-900">
                  {report.final_score.toFixed(1)}
                </p>
                <p className="text-xs text-gray-500 mt-1">Final Score</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-semibold text-gray-700">
                  {report.interview_score.toFixed(1)}
                </p>
                <p className="text-xs text-gray-500 mt-1">Interview</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-semibold text-gray-700">
                  {report.resume_score > 0
                    ? report.resume_score.toFixed(1)
                    : "—"}
                </p>
                <p className="text-xs text-gray-500 mt-1">Resume</p>
              </div>
            </div>

            <div className="text-right">
              <p className="text-lg font-semibold text-gray-800">
                {(report.confidence * 100).toFixed(0)}%
              </p>
              <p className="text-xs text-gray-500">Confidence</p>
              {report.borderline && (
                <Badge variant="outline" className="mt-1 text-xs text-amber-700 border-amber-300">
                  Borderline
                </Badge>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Dimension scores chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Dimension Scores</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={chartData}
              margin={{ top: 8, right: 16, left: -10, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11 }}
                tickLine={false}
              />
              <YAxis
                domain={[0, 10]}
                tick={{ fontSize: 11 }}
                tickLine={false}
              />
              <Tooltip
                formatter={(value) =>
                  typeof value === "number"
                    ? [value.toFixed(2), "Score"]
                    : [String(value), "Score"]
                }
              />
              <ReferenceLine
                y={5}
                stroke="#ef4444"
                strokeDasharray="4 2"
                strokeWidth={1}
                label={{
                  value: "Floor",
                  position: "insideTopRight",
                  fontSize: 10,
                  fill: "#ef4444",
                }}
              />
              <Bar dataKey="score" radius={[4, 4, 0, 0]} maxBarSize={48}>
                {chartData.map((entry, i) => (
                  <Cell
                    key={i}
                    fill={entry.violated ? "#ef4444" : "#3b82f6"}
                    fillOpacity={0.85}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-gray-400 mt-2">
            Red bars = floor violation. Red dashed line = minimum floor (5.0).
          </p>
        </CardContent>
      </Card>

      {/* Floor violations */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Floor Checks</CardTitle>
        </CardHeader>
        <CardContent>
          {report.floor_violations.length === 0 ? (
            <p className="text-sm text-green-700 flex items-center gap-1.5">
              <span>✓</span> All dimension floors passed
            </p>
          ) : (
            <div className="space-y-1">
              {report.floor_violations.map((dim) => (
                <p key={dim} className="text-sm text-red-600 flex items-center gap-1.5">
                  <span>✗</span>
                  <span>
                    {DIMENSION_LABELS[dim] ?? dim} below minimum (
                    {FLOOR_THRESHOLDS[dim]?.toFixed(1) ?? "?"})
                  </span>
                </p>
              ))}
              {report.floor_override && (
                <p className="text-sm text-red-700 font-medium mt-2">
                  → Tier overridden to Reject due to floor violations
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Hallucination summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Integrity Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          {hallucinationPenalty === 0 ? (
            <p className="text-sm text-green-700 flex items-center gap-1.5">
              <span>✓</span> No issues detected
            </p>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-gray-600">
                Total penalty applied:{" "}
                <span className="font-semibold text-red-600">
                  {hallucinationPenalty.toFixed(2)} points
                </span>
              </p>
              {report.bluff_carry && (
                <p className="text-sm text-amber-700">
                  ⚠ Bluff-carry penalty applied (≥2 answers with experience bluff detected)
                </p>
              )}
              <div className="text-xs text-gray-500 mt-1">
                {Object.entries(HALLUCINATION_LABELS).map(([key, label]) => (
                  <p key={key}>{label}</p>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recruiter summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">AI Recruiter Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-700 leading-relaxed">
            Evaluation generated on{" "}
            {new Date(report.evaluated_at).toLocaleString()}.
          </p>
        </CardContent>
      </Card>

      {/* Audit trace */}
      <Card>
        <CardHeader>
          <button
            className="flex w-full items-center justify-between text-base font-semibold text-gray-900"
            onClick={() => setAuditOpen((v) => !v)}
          >
            Audit Trace
            {auditOpen ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>
        </CardHeader>
        {auditOpen && (
          <CardContent>
            <pre className="text-xs text-gray-600 bg-gray-50 rounded-md p-3 overflow-auto whitespace-pre-wrap">
              {JSON.stringify(
                {
                  tier: report.tier,
                  final_score: report.final_score,
                  interview_score: report.interview_score,
                  resume_score: report.resume_score,
                  hallucination_penalty: report.hallucination_penalty,
                  floor_violations: report.floor_violations,
                  floor_override: report.floor_override,
                  bluff_carry: report.bluff_carry,
                  confidence: report.confidence,
                  borderline: report.borderline,
                  evaluated_at: report.evaluated_at,
                },
                null,
                2
              )}
            </pre>
          </CardContent>
        )}
      </Card>
    </div>
  );
}
