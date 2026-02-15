import type { QuestionTypeOption, PaperConfig } from "@/types/paper-editor";
import type { DropAnimation } from "@dnd-kit/core";
import { defaultDropAnimationSideEffects } from "@dnd-kit/core";

export const QUESTION_TYPES: QuestionTypeOption[] = [
  { value: "single_choice", label: "单选题", color: "bg-blue-500" },
  { value: "multiple_choice", label: "多选题", color: "bg-purple-500" },
  { value: "fill", label: "填空题", color: "bg-orange-500" },
  { value: "problem", label: "解答题", color: "bg-green-500" },
];

export const DEFAULT_SCORES: Record<string, number> = {
  single_choice: 5,
  multiple_choice: 5,
  fill: 5,
  problem: 12,
};

export const DEFAULT_PAPER_CONFIG: PaperConfig = {
  subject: "数学",
  title: "",
  school: "",
  examTime: "",
  duration: "120",
};

export { API_BASE } from "./constants";

export const getBadgeClass = (type: string): string => {
  switch (type) {
    case "single_choice":
      return "bg-blue-50 text-blue-700 border-blue-200 hover:bg-blue-100";
    case "multiple_choice":
      return "bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100";
    case "fill":
      return "bg-orange-50 text-orange-700 border-orange-200 hover:bg-orange-100";
    case "problem":
      return "bg-green-50 text-green-700 border-green-200 hover:bg-green-100";
    default:
      return "bg-muted text-muted-foreground";
  }
};

export const getTypeLabel = (type: string): string => {
  return QUESTION_TYPES.find((t) => t.value === type)?.label || type;
};

export const getSectionTitle = (type: string, index: number): string => {
  const chineseNums = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"];
  const numStr = index < chineseNums.length ? chineseNums[index] : String(index + 1);
  return `${numStr}、${getTypeLabel(type)}`;
};

export const dropAnimation: DropAnimation = {
  sideEffects: defaultDropAnimationSideEffects({
    styles: {
      active: {
        opacity: "0.5",
      },
    },
  }),
};
