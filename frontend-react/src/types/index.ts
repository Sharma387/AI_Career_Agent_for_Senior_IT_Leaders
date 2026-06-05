export interface User {
  id: number;
  email: string;
  full_name: string;
  is_active: boolean;
  created_at: string;
}

export interface Skill {
  id: number;
  name: string;
  category: string;
  proficiency?: string;
}

export interface Certification {
  name: string;
  issuer?: string;
  date_obtained?: string;
  expiry_date?: string;
}

export interface CareerProfile {
  id: number;
  profile_id?: number;
  full_name: string;
  email: string;
  phone?: string;
  linkedin_url?: string;
  summary: string;
  raw_resume_text: string;
  formatted_resume_html?: string;
  interests?: string[];
  education?: Education[];
  skills: Skill[];
  certifications: Certification[];
  projects: Project[];
  created_at: string;
  updated_at?: string;
}

export interface Education {
  degree: string;
  institution: string;
  year: string;
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

export interface ScoreComponent {
  score: number;
  max: number;
  weight: number;
  weighted: number;
}

export interface MatchScoreBreakdown {
  skills_match: ScoreComponent;
  experience_match: ScoreComponent;
  industry_relevance: ScoreComponent;
  leadership_signals: ScoreComponent;
}

export interface ImprovementRecommendation {
  area: string;
  gap: string;
  recommendation: string;
  priority: 'high' | 'medium' | 'low';
  estimated_impact: string;
}

export interface MatchResult {
  match_id: string;
  match_score: number;
  score_breakdown?: MatchScoreBreakdown;
  strengths: string[];
  gaps: string[];
  evidence: Array<string | { career_chunk: string; relevance: string }>;
  explanation: string;
  recommendation: string;
  improvement_recommendations?: ImprovementRecommendation[];
}

export interface InterviewStrategy {
  job_id: number;
  profile_id: number;
  match_score: number;
  strengths: string[];
  gaps: string[];
  explanation: string;
  recommendation: string;
  key_themes: string[];
  potential_questions: string[];
  talking_points: string[];
  areas_to_prepare: string[];
  improvement_recommendations?: ImprovementRecommendation[];
}

export interface SecretQuestion {
  id: number;
  question: string;
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
