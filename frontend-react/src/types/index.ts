export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface CareerProfile {
  id: number;
  profile_id?: number;
  full_name: string;
  email: string;
  summary: string;
  raw_resume_text: string;
  created_at: string;
}

export interface Project {
  id?: number;
  title: string;
  description: string;
  role: string;
  technologies: string[];
  impact: string;
  star_situation: string;
  star_task: string;
  star_action: string;
  star_result: string;
}

export interface JobPosting {
  id: number;
  title: string;
  company: string;
  description: string;
  location: string;
  seniority_level: string;
  source: string;
  created_at: string;
}

export interface Application {
  application_id: number;
  status: string;
  date_applied: string;
  last_updated: string;
  feedback_notes: string;
  has_materials: boolean;
  job: JobPosting;
}

export interface MatchResult {
  match_id: string;
  match_score: number;
  strengths: string[];
  gaps: string[];
  evidence: string[];
  explanation: string;
  recommendation: string;
}

export interface ApplicationStats {
  total_applied: number;
  interview_count: number;
  rejection_count: number;
  offer_count: number;
  success_rate: number;
  interview_rate: number;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}
