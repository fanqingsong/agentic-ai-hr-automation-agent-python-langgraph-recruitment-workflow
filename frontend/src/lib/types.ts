/**
 * TypeScript type definitions
 */

export type UserRole = 'job_seeker' | 'hr_manager' | 'admin';

export interface User {
  id: string;
  email: string;
  name: string;
  role: UserRole;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface JobPost {
  id?: string;
  ulid: string;
  jobApplication: {
    title: string;
    description_html: string;
    description?: string;
  };
  hr: {
    name: string;
    email: string;
  };
  created_at?: string;
}

export interface Candidate {
  id: string;
  candidate_name: string;
  candidate_email: string;
  job_id: string;
  score?: number;
  summary?: string;
  reasoning?: string;
  evaluation?: {
    score: number;
    decision: string;
    reasoning: string;
    strengths: string[];
    gaps: string[];
  };
  skills_match?: {
    strong: string[];
    partial: string[];
    missing: string[];
  };
  cv_url?: string;
  created_at: string;
}

export interface DashboardStats {
  total_candidates: number;
  average_score: number;
  high_score_count: number;
  recent_applications: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  refresh_token?: string;
}
