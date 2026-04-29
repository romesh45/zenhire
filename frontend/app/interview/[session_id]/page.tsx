"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { resumes, sessions, type QuestionResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";

type Step = "upload" | "interview" | "complete";

type ErrorKind = "not_found" | "expired" | "already_complete" | "generic";

interface AppError {
  kind: ErrorKind;
  message: string;
}

const MIN_ANSWER_LENGTH = 50;
const MAX_FILE_SIZE_MB = 5;

function classifyError(msg: string): AppError {
  if (msg.includes("not found") || msg.includes("404"))
    return { kind: "not_found", message: "Invalid interview link." };
  if (msg.includes("expired"))
    return { kind: "expired", message: "This interview link has expired." };
  if (msg.includes("already") || msg.includes("completed"))
    return {
      kind: "already_complete",
      message: "This interview has already been completed.",
    };
  return { kind: "generic", message: msg };
}

export default function CandidateInterviewPage() {
  const params = useParams();
  const sessionId = params.session_id as string;

  const [step, setStep] = useState<Step>("upload");

  // Session-level fatal error (renders a dedicated screen)
  const [fatalError, setFatalError] = useState<AppError | null>(null);

  // Form-level inline errors
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Upload step
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadMessage, setUploadMessage] = useState<string | null>(null);

  // Interview step
  const [question, setQuestion] = useState<QuestionResponse | null>(null);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [followupMessage, setFollowupMessage] = useState<string | null>(null);
  const [questionIndex, setQuestionIndex] = useState(1);

  // Check session state on mount
  useEffect(() => {
    async function checkSession() {
      try {
        const q = await sessions.getQuestion(sessionId);
        // Session is already active — resume interview
        setQuestion(q);
        setStep("interview");
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        if (msg.includes("completed") || msg.includes("all questions answered")) {
          setStep("complete");
          return;
        }
        if (msg.includes("not found") && !msg.toLowerCase().includes("state")) {
          setFatalError(classifyError(msg));
          return;
        }
        // Session is pending — stay on upload step
      }
    }
    checkSession();
  }, [sessionId]);

  async function handleUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;

    if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
      setUploadError(`File too large. Max size is ${MAX_FILE_SIZE_MB}MB.`);
      return;
    }

    setUploading(true);
    setUploadMessage("Uploading resume…");
    setUploadError(null);

    try {
      const uploadRes = await resumes.upload(sessionId, file);
      setUploadMessage("Analysing your resume… (~5–10 seconds)");
      await sessions.start(sessionId, uploadRes.resume_id);
      setUploadMessage("Done! Loading your first question…");
      const q = await sessions.getQuestion(sessionId);
      setQuestion(q);
      setStep("interview");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Upload failed";
      const classified = classifyError(msg);
      if (
        classified.kind === "not_found" ||
        classified.kind === "expired"
      ) {
        setFatalError(classified);
      } else {
        setUploadError(classified.message);
      }
    } finally {
      setUploading(false);
      setUploadMessage(null);
    }
  }

  const handleSubmitAnswer = useCallback(async () => {
    if (!question || answer.trim().length < MIN_ANSWER_LENGTH) return;

    setSubmitting(true);
    setFollowupMessage(null);
    setSubmitError(null);

    try {
      const res = await sessions.submitAnswer(sessionId, answer);

      if (res.session_status === "completed") {
        setStep("complete");
        return;
      }

      if (res.next_question) {
        if (res.next_question.question_id === question.question_id) {
          setFollowupMessage(res.message);
          setQuestion(res.next_question);
          setAnswer("");
        } else {
          setFollowupMessage(null);
          setQuestion(res.next_question);
          setAnswer("");
          setQuestionIndex((i) => i + 1);
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Submission failed";
      setSubmitError(msg);
    } finally {
      setSubmitting(false);
    }
  }, [question, answer, sessionId]);

  // ── Fatal error screen ──────────────────────────────────────────────────────
  if (fatalError) {
    const title =
      fatalError.kind === "not_found"
        ? "Invalid interview link"
        : fatalError.kind === "expired"
        ? "Link expired"
        : fatalError.kind === "already_complete"
        ? "Interview complete"
        : "Something went wrong";

    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <Card className="w-full max-w-md text-center">
          <CardContent className="pt-8 pb-8 space-y-3">
            <p className="text-4xl">⚠️</p>
            <p className="text-lg font-semibold text-gray-900">{title}</p>
            <p className="text-sm text-gray-500">{fatalError.message}</p>
          </CardContent>
        </Card>
      </main>
    );
  }

  // ── Complete screen ─────────────────────────────────────────────────────────
  if (step === "complete") {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <Card className="w-full max-w-md text-center">
          <CardContent className="pt-8 pb-8 space-y-4">
            <p className="text-4xl">🎉</p>
            <h1 className="text-xl font-bold text-gray-900">
              Thank you! Your interview is complete.
            </h1>
            <p className="text-sm text-gray-500 leading-relaxed">
              Your recruiter will review your evaluation shortly. You can close
              this window.
            </p>
          </CardContent>
        </Card>
      </main>
    );
  }

  // ── Upload step ─────────────────────────────────────────────────────────────
  if (step === "upload") {
    return (
      <main className="flex min-h-screen items-center justify-center px-4">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-xl text-center">
              Welcome to your interview
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-500 text-center mb-6">
              Please upload your resume (PDF) to begin. This helps us tailor
              your questions.
            </p>

            {uploadMessage ? (
              <div className="space-y-4 text-center py-4">
                <div className="w-8 h-8 border-4 border-gray-300 border-t-gray-900 rounded-full animate-spin mx-auto" />
                <p className="text-sm text-gray-600">{uploadMessage}</p>
              </div>
            ) : (
              <form onSubmit={handleUpload} className="space-y-4">
                <div
                  className="border-2 border-dashed border-gray-200 rounded-lg px-6 py-8 text-center cursor-pointer hover:border-gray-400 transition-colors"
                  onClick={() =>
                    document.getElementById("resume-input")?.click()
                  }
                >
                  {file ? (
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {file.name}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {(file.size / 1024).toFixed(0)} KB
                      </p>
                    </div>
                  ) : (
                    <>
                      <p className="text-sm text-gray-500">
                        Click to select your PDF resume
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        PDF only, max {MAX_FILE_SIZE_MB}MB
                      </p>
                    </>
                  )}
                  <input
                    id="resume-input"
                    type="file"
                    accept=".pdf,application/pdf"
                    className="hidden"
                    onChange={(e) => {
                      setFile(e.target.files?.[0] ?? null);
                      setUploadError(null);
                    }}
                  />
                </div>

                {uploadError && (
                  <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-md text-center">
                    {uploadError}
                  </p>
                )}

                <Button
                  type="submit"
                  className="w-full"
                  disabled={!file || uploading}
                >
                  {uploading ? "Processing…" : "Start Interview"}
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </main>
    );
  }

  // ── Interview step ──────────────────────────────────────────────────────────
  const charCount = answer.trim().length;
  const readyToSubmit = charCount >= MIN_ANSWER_LENGTH;

  return (
    <main className="min-h-screen bg-gray-50 flex items-start justify-center px-4 py-12">
      <div className="w-full max-w-xl space-y-6">
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-gray-500">
            <span>Question {questionIndex} of 6</span>
            {question && (
              <span className="capitalize text-gray-400">
                {question.difficulty}
              </span>
            )}
          </div>
          <Progress value={(questionIndex / 6) * 100} className="h-1.5" />
        </div>

        <Card>
          <CardHeader>
            {followupMessage && (
              <div className="mb-3 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2">
                <strong>Follow-up:</strong> {followupMessage}
              </div>
            )}
            <CardTitle className="text-base font-medium leading-relaxed text-gray-900">
              {question?.question_text}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Type your answer here…"
              rows={7}
              className="w-full rounded-lg border border-gray-200 px-4 py-3 text-sm text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent resize-none"
            />

            <div className="flex items-center justify-between">
              <span
                className={`text-xs ${
                  readyToSubmit ? "text-green-600" : "text-gray-400"
                }`}
              >
                {charCount} / {MIN_ANSWER_LENGTH} min chars
                {readyToSubmit && " ✓"}
              </span>
              <Button
                onClick={handleSubmitAnswer}
                disabled={!readyToSubmit || submitting}
              >
                {submitting ? "Submitting…" : "Submit Answer"}
              </Button>
            </div>

            {submitError && (
              <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-md">
                {submitError}
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
