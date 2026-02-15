// API helper functions

import { API_BASE } from "./constants";
import type { Question, QuestionFormData } from "@/types/question";

// ============ Questions API ============

export async function fetchQuestions(): Promise<Question[]> {
  const response = await fetch(`${API_BASE}/api/questions`);
  if (!response.ok) throw new Error("加载题库失败");
  const data = await response.json();
  return data.questions || [];
}

export async function createQuestion(payload: QuestionFormData): Promise<void> {
  const response = await fetch(`${API_BASE}/api/questions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || "创建题目失败");
  }
}

export async function updateQuestion(id: string, payload: Partial<Question>): Promise<void> {
  const response = await fetch(`${API_BASE}/api/questions/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || "更新题目失败");
  }
}

export async function deleteQuestion(id: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/questions/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || "删除题目失败");
  }
}

export async function bulkDeleteQuestions(ids: string[]): Promise<{ deleted: number }> {
  const response = await fetch(`${API_BASE}/api/questions/bulk-delete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail || "批量删除失败");
  }
  return response.json();
}

export async function importQuestions(jsonData: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/api/questions/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ json_data: jsonData }),
  });
  const result = await response.json();
  if (!result.success) {
    throw new Error(result.message);
  }
  return result;
}

export async function generateAnswer(questionId: string): Promise<{ success: boolean; answer?: string; analysis?: string; message?: string }> {
  const response = await fetch(`${API_BASE}/api/questions/${questionId}/generate-answer`, {
    method: "POST",
  });
  return response.json();
}

export async function generateTags(questionId: string): Promise<{ success: boolean; tags?: string[]; difficulty?: string; message?: string }> {
  const response = await fetch(`${API_BASE}/api/questions/${questionId}/generate-tags`, {
    method: "POST",
  });
  return response.json();
}
