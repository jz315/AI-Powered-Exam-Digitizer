// Question types and interfaces

export interface SubQuestion {
  content: string;
  sub_questions?: SubQuestion[];
}

export interface Question {
  id: string;
  content: string;
  type: string;
  options?: string[];
  difficulty?: string;
  tags?: string[];
  answer?: string;
  analysis?: string;
  sub_questions?: SubQuestion[];
  starred?: boolean;
}

export type QuestionType = "single_choice" | "multiple_choice" | "fill" | "problem";

export type DifficultyLevel = "easy" | "medium" | "hard";

export interface QuestionFormData {
  content: string;
  type: string;
  options?: string[];
  difficulty?: string;
  tags?: string[];
  answer?: string;
  analysis?: string;
  sub_questions?: SubQuestion[];
}

export const emptyQuestionForm: QuestionFormData = {
  content: "",
  type: "single_choice",
  options: ["", "", "", ""],
  difficulty: "medium",
  tags: [],
  answer: "",
  analysis: "",
  sub_questions: [],
};
