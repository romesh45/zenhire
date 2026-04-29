const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("zenhire_token");
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail))
        detail = body.detail.map((d: { msg: string }) => d.msg).join(", ");
    } catch {
      // ignore parse errors
    }
    throw new Error(detail);
  }

  return res.json() as Promise<T>;
}

// ── Types ────────────────────────────────────────────────────────────────────

export interface RecruiterResponse {
  id: string;
  name: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface JobResponse {
  id: string;
  title: string;
  description: string | null;
  required_skills: string[];
  dimension_weights: Record<string, number>;
  created_by_recruiter_id: string;
  created_at: string;
}

export interface SessionInviteResponse {
  session_id: string;
  candidate_url: string;
}

export interface SessionStartResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface QuestionResponse {
  question_id: string;
  question_text: string;
  difficulty: string;
  followup_count: number;
}

export interface AnswerSubmitResponse {
  next_question: QuestionResponse | null;
  session_status: string;
  message: string;
}

export interface EvaluationStatusResponse {
  total_answers: number;
  evaluated: number;
  pending: number;
  all_complete: boolean;
}

export interface DimensionAverages {
  technical_accuracy: number;
  depth_of_explanation: number;
  problem_solving: number;
  communication_clarity: number;
  relevance: number;
  reasoning_quality: number;
}

export interface DecisionReport {
  tier: "strong_hire" | "hire" | "maybe" | "reject";
  final_score: number;
  interview_score: number;
  resume_score: number;
  dimension_averages: DimensionAverages;
  floor_violations: string[];
  floor_override: boolean;
  hallucination_penalty: number;
  bluff_carry: boolean;
  confidence: number;
  borderline: boolean;
  evaluated_at: string;
}

export interface ReportResponse {
  report_id: string;
  session_id: string;
  created_at: string;
  report: DecisionReport;
}

export interface ResumeUploadResponse {
  resume_id: string;
  session_id: string;
  filename: string;
}

// ── API surface ───────────────────────────────────────────────────────────────

export const auth = {
  register: (name: string, email: string, password: string) =>
    apiFetch<RecruiterResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ name, email, password }),
    }),

  login: (email: string, password: string) =>
    apiFetch<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
};

export const jobs = {
  create: (data: {
    title: string;
    description?: string;
    required_skills?: string[];
    dimension_weights?: Record<string, number>;
  }) =>
    apiFetch<JobResponse>("/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  list: () => apiFetch<JobResponse[]>("/jobs"),
};

export const sessions = {
  invite: (job_id: string, candidate_name: string, candidate_email: string) =>
    apiFetch<SessionInviteResponse>("/sessions/invite", {
      method: "POST",
      body: JSON.stringify({ job_id, candidate_name, candidate_email }),
    }),

  start: (session_id: string, resume_id: string) =>
    apiFetch<SessionStartResponse>(`/sessions/${session_id}/start`, {
      method: "POST",
      body: JSON.stringify({ resume_id }),
    }),

  getQuestion: (session_id: string) =>
    apiFetch<QuestionResponse>(`/sessions/${session_id}/question`),

  submitAnswer: (session_id: string, answer_text: string) =>
    apiFetch<AnswerSubmitResponse>(`/sessions/${session_id}/answer`, {
      method: "POST",
      body: JSON.stringify({ answer_text }),
    }),

  evaluationStatus: (session_id: string) =>
    apiFetch<EvaluationStatusResponse>(
      `/sessions/${session_id}/evaluation-status`
    ),

  evaluate: (session_id: string) =>
    apiFetch<ReportResponse>(`/sessions/${session_id}/evaluate`, {
      method: "POST",
    }),

  getReport: (session_id: string) =>
    apiFetch<ReportResponse>(`/sessions/${session_id}/report`),
};

export const resumes = {
  upload: async (session_id: string, file: File): Promise<ResumeUploadResponse> => {
    const token = getToken();
    const formData = new FormData();
    formData.append("session_id", session_id);
    formData.append("file", file);

    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${API_URL}/resumes/upload`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const body = await res.json();
        if (typeof body.detail === "string") detail = body.detail;
      } catch {
        // ignore
      }
      throw new Error(detail);
    }

    return res.json() as Promise<ResumeUploadResponse>;
  },
};
