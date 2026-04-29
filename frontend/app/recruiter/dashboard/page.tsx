"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { jobs as jobsApi, sessions as sessionsApi, type JobResponse } from "@/lib/api";
import { useAuthStore } from "@/lib/store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Copy, Check, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";

const DIMENSION_KEYS = [
  "technical_accuracy",
  "depth_of_explanation",
  "problem_solving",
  "communication_clarity",
  "relevance",
  "reasoning_quality",
] as const;

const DIMENSION_LABELS: Record<string, string> = {
  technical_accuracy: "Technical Accuracy",
  depth_of_explanation: "Depth of Explanation",
  problem_solving: "Problem Solving",
  communication_clarity: "Communication Clarity",
  relevance: "Relevance",
  reasoning_quality: "Reasoning Quality",
};

type DimensionKey = (typeof DIMENSION_KEYS)[number];

function normalise(weights: Record<string, number>): Record<string, number> {
  const total = Object.values(weights).reduce((a, b) => a + b, 0);
  if (total === 0) return weights;
  return Object.fromEntries(
    Object.entries(weights).map(([k, v]) => [k, v / total])
  );
}

export default function DashboardPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { recruiter, token, clearAuth } = useAuthStore();

  // Redirect if unauthenticated
  useEffect(() => {
    if (!token) router.push("/recruiter/login");
  }, [token, router]);

  // ── Jobs list ────────────────────────────────────────────────────────────
  const { data: jobsList, isLoading: jobsLoading } = useQuery({
    queryKey: ["jobs"],
    queryFn: jobsApi.list,
    enabled: !!token,
  });

  // ── Create job form ───────────────────────────────────────────────────────
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [jobTitle, setJobTitle] = useState("");
  const [jobDescription, setJobDescription] = useState("");
  const [skillsInput, setSkillsInput] = useState("");
  const [weights, setWeights] = useState<Record<DimensionKey, number>>({
    technical_accuracy: 0.25,
    depth_of_explanation: 0.15,
    problem_solving: 0.25,
    communication_clarity: 0.15,
    relevance: 0.10,
    reasoning_quality: 0.10,
  });
  const [createError, setCreateError] = useState<string | null>(null);

  const weightSum = Object.values(weights).reduce((a, b) => a + b, 0);

  const createJobMutation = useMutation({
    mutationFn: () =>
      jobsApi.create({
        title: jobTitle,
        description: jobDescription || undefined,
        required_skills: skillsInput
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        dimension_weights: normalise(weights),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      setShowCreateForm(false);
      setJobTitle("");
      setJobDescription("");
      setSkillsInput("");
      setCreateError(null);
    },
    onError: (err: Error) => setCreateError(err.message),
  });

  // ── Invite candidate ─────────────────────────────────────────────────────
  const [inviteJob, setInviteJob] = useState<JobResponse | null>(null);
  const [candidateName, setCandidateName] = useState("");
  const [candidateEmail, setCandidateEmail] = useState("");
  const [inviteResult, setInviteResult] = useState<{
    session_id: string;
    candidate_url: string;
  } | null>(null);
  const [copied, setCopied] = useState(false);
  const [inviteError, setInviteError] = useState<string | null>(null);

  // Track recent sessions per job
  const [recentSessions, setRecentSessions] = useState<
    Record<string, { session_id: string; candidate_name: string }[]>
  >(() => {
    if (typeof window === "undefined") return {};
    try {
      return JSON.parse(localStorage.getItem("zenhire_sessions") ?? "{}");
    } catch {
      return {};
    }
  });

  const inviteMutation = useMutation({
    mutationFn: () =>
      sessionsApi.invite(inviteJob!.id, candidateName, candidateEmail),
    onSuccess: (data) => {
      setInviteResult(data);
      setInviteError(null);
      // Persist session
      const updated = {
        ...recentSessions,
        [inviteJob!.id]: [
          ...(recentSessions[inviteJob!.id] ?? []),
          { session_id: data.session_id, candidate_name: candidateName },
        ],
      };
      setRecentSessions(updated);
      localStorage.setItem("zenhire_sessions", JSON.stringify(updated));
    },
    onError: (err: Error) => setInviteError(err.message),
  });

  function closeInviteDialog() {
    setInviteJob(null);
    setCandidateName("");
    setCandidateEmail("");
    setInviteResult(null);
    setCopied(false);
    setInviteError(null);
  }

  async function handleCopy(url: string) {
    await navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  if (!token) return null;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-gray-900">Zenhire</h1>
          <p className="text-sm text-gray-500">
            Welcome, {recruiter?.name ?? "Recruiter"}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            clearAuth();
            router.push("/recruiter/login");
          }}
        >
          Logout
        </Button>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-8">
        {/* Create Job */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Create New Job</h2>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowCreateForm((v) => !v)}
            >
              {showCreateForm ? (
                <><ChevronUp className="w-4 h-4 mr-1" /> Hide</>
              ) : (
                <><ChevronDown className="w-4 h-4 mr-1" /> New Job</>
              )}
            </Button>
          </div>

          {showCreateForm && (
            <Card>
              <CardContent className="pt-6 space-y-5">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="sm:col-span-2 space-y-1.5">
                    <Label>Job Title *</Label>
                    <Input
                      value={jobTitle}
                      onChange={(e) => setJobTitle(e.target.value)}
                      placeholder="Senior Python Engineer"
                    />
                  </div>
                  <div className="sm:col-span-2 space-y-1.5">
                    <Label>Description</Label>
                    <Input
                      value={jobDescription}
                      onChange={(e) => setJobDescription(e.target.value)}
                      placeholder="Brief job description…"
                    />
                  </div>
                  <div className="sm:col-span-2 space-y-1.5">
                    <Label>Required Skills (comma separated)</Label>
                    <Input
                      value={skillsInput}
                      onChange={(e) => setSkillsInput(e.target.value)}
                      placeholder="Python, FastAPI, PostgreSQL"
                    />
                  </div>
                </div>

                {/* Dimension Weights */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label className="text-sm font-medium">Dimension Weights</Label>
                    <span
                      className={`text-xs font-mono ${
                        Math.abs(weightSum - 1.0) > 0.01
                          ? "text-amber-600"
                          : "text-green-600"
                      }`}
                    >
                      Sum: {weightSum.toFixed(2)}{" "}
                      {Math.abs(weightSum - 1.0) > 0.01
                        ? "⚠ should be 1.0"
                        : "✓"}
                    </span>
                  </div>
                  <div className="space-y-2">
                    {DIMENSION_KEYS.map((key) => (
                      <div key={key} className="flex items-center gap-3">
                        <span className="text-sm text-gray-600 w-44 shrink-0">
                          {DIMENSION_LABELS[key]}
                        </span>
                        <input
                          type="range"
                          min={0}
                          max={1}
                          step={0.05}
                          value={weights[key]}
                          onChange={(e) =>
                            setWeights((w) => ({
                              ...w,
                              [key]: parseFloat(e.target.value),
                            }))
                          }
                          className="flex-1"
                        />
                        <span className="text-sm font-mono w-10 text-right text-gray-700">
                          {weights[key].toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

                {createError && (
                  <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-md">
                    {createError}
                  </p>
                )}

                <Button
                  onClick={() => {
                    if (!jobTitle.trim()) {
                      setCreateError("Job title is required");
                      return;
                    }
                    createJobMutation.mutate();
                  }}
                  disabled={createJobMutation.isPending}
                >
                  {createJobMutation.isPending ? "Creating…" : "Create Job"}
                </Button>
              </CardContent>
            </Card>
          )}
        </section>

        {/* Jobs List */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Your Jobs</h2>

          {jobsLoading && (
            <p className="text-sm text-gray-400">Loading jobs…</p>
          )}

          {!jobsLoading && (!jobsList || jobsList.length === 0) && (
            <p className="text-sm text-gray-400">
              No jobs yet. Create your first job above.
            </p>
          )}

          <div className="space-y-4">
            {jobsList?.map((job) => (
              <Card key={job.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <CardTitle className="text-base">{job.title}</CardTitle>
                      {job.description && (
                        <CardDescription className="mt-1 text-sm">
                          {job.description}
                        </CardDescription>
                      )}
                    </div>
                    <Button
                      size="sm"
                      onClick={() => setInviteJob(job)}
                    >
                      Invite Candidate
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  {job.required_skills.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {job.required_skills.map((skill) => (
                        <Badge key={skill} variant="secondary" className="text-xs">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {/* Recent sessions */}
                  {(recentSessions[job.id] ?? []).length > 0 && (
                    <div className="pt-2 border-t">
                      <p className="text-xs font-medium text-gray-500 mb-1.5">
                        Recent sessions
                      </p>
                      <div className="space-y-1">
                        {(recentSessions[job.id] ?? []).map((s) => (
                          <div
                            key={s.session_id}
                            className="flex items-center justify-between text-sm"
                          >
                            <span className="text-gray-600">
                              {s.candidate_name}
                            </span>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 text-xs"
                              onClick={() =>
                                router.push(
                                  `/recruiter/sessions/${s.session_id}`
                                )
                              }
                            >
                              View <ExternalLink className="w-3 h-3 ml-1" />
                            </Button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      </main>

      {/* Invite Dialog */}
      <Dialog open={!!inviteJob} onOpenChange={(open) => !open && closeInviteDialog()}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Invite Candidate</DialogTitle>
            <DialogDescription>
              {inviteJob?.title} — send this link to your candidate
            </DialogDescription>
          </DialogHeader>

          {!inviteResult ? (
            <div className="space-y-4 pt-2">
              <div className="space-y-1.5">
                <Label>Candidate Name</Label>
                <Input
                  value={candidateName}
                  onChange={(e) => setCandidateName(e.target.value)}
                  placeholder="Alex Johnson"
                />
              </div>
              <div className="space-y-1.5">
                <Label>Candidate Email</Label>
                <Input
                  type="email"
                  value={candidateEmail}
                  onChange={(e) => setCandidateEmail(e.target.value)}
                  placeholder="alex@example.com"
                />
              </div>
              {inviteError && (
                <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-md">
                  {inviteError}
                </p>
              )}
              <Button
                className="w-full"
                onClick={() => inviteMutation.mutate()}
                disabled={
                  inviteMutation.isPending ||
                  !candidateName.trim() ||
                  !candidateEmail.trim()
                }
              >
                {inviteMutation.isPending ? "Creating invite…" : "Create Invite Link"}
              </Button>
            </div>
          ) : (
            <div className="space-y-4 pt-2">
              <p className="text-sm text-gray-600">
                Share this link with{" "}
                <strong>{candidateName}</strong>:
              </p>
              <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2">
                <code className="flex-1 text-xs text-gray-700 break-all">
                  {inviteResult.candidate_url}
                </code>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleCopy(inviteResult.candidate_url)}
                >
                  {copied ? (
                    <Check className="w-4 h-4 text-green-600" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="flex-1"
                  onClick={() =>
                    router.push(
                      `/recruiter/sessions/${inviteResult.session_id}`
                    )
                  }
                >
                  View Session <ExternalLink className="w-3 h-3 ml-1" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={closeInviteDialog}
                >
                  Done
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
