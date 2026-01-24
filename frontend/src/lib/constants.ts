// Shared constants

import type { QuestionType, DifficultyLevel } from "@/types/question";

export const API_BASE = "http://127.0.0.1:8000";

export const QUESTION_TYPES: { value: QuestionType; label: string }[] = [
  { value: "single_choice", label: "单选题" },
  { value: "multiple_choice", label: "多选题" },
  { value: "fill", label: "填空题" },
  { value: "problem", label: "解答题" },
];

export const DIFFICULTIES: { value: DifficultyLevel; label: string }[] = [
  { value: "easy", label: "简单" },
  { value: "medium", label: "中等" },
  { value: "hard", label: "困难" },
];

export const DEFAULT_SCORES: Record<string, number> = {
  single_choice: 5,
  multiple_choice: 5,
  fill: 5,
  problem: 12,
};

// Badge color classes for question types
export function getBadgeClass(type: string): string {
  switch (type) {
    case "single_choice": return "badge-gradient-blue";
    case "multiple_choice": return "badge-gradient-purple";
    case "fill": return "badge-gradient-orange";
    case "problem": return "badge-gradient-green";
    default: return "bg-muted text-muted-foreground";
  }
}

// Tag color classes (deterministic based on tag string)
export function getTagColor(tag: string): string {
  const colors = [
    "bg-blue-500/20 text-blue-600 dark:text-blue-400 border-blue-500/30",
    "bg-green-500/20 text-green-600 dark:text-green-400 border-green-500/30",
    "bg-purple-500/20 text-purple-600 dark:text-purple-400 border-purple-500/30",
    "bg-orange-500/20 text-orange-600 dark:text-orange-400 border-orange-500/30",
    "bg-pink-500/20 text-pink-600 dark:text-pink-400 border-pink-500/30",
    "bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 border-cyan-500/30",
    "bg-amber-500/20 text-amber-600 dark:text-amber-400 border-amber-500/30",
    "bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border-indigo-500/30",
  ];
  const hash = tag.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return colors[hash % colors.length];
}

export function getTypeLabel(type: string): string {
  return QUESTION_TYPES.find(t => t.value === type)?.label || type;
}

export function getDifficultyLabel(diff: string): string {
  return DIFFICULTIES.find(d => d.value === diff)?.label || diff;
}
