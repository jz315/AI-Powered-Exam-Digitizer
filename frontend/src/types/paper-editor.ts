import type { CartQuestion } from "@/contexts/PaperCartContext";

export interface Question {
  id: string;
  content: string;
  type: string;
  options?: string[];
  difficulty?: string;
  tags?: string[];
  answer?: string;
  analysis?: string;
  sub_questions?: unknown[];
  starred?: boolean;
}

export interface PaperQuestion extends CartQuestion {
  score: number;
}

export interface Section {
  id: string;
  title: string;
  type: string;
  questions: PaperQuestion[];
  collapsed?: boolean;
}

export type QuestionType = "single_choice" | "multiple_choice" | "fill" | "problem";

export interface QuestionTypeOption {
  value: QuestionType;
  label: string;
  color: string;
}

export interface PaperConfig {
  subject: string;
  title: string;
  school: string;
  examTime: string;
  duration: string;
}
