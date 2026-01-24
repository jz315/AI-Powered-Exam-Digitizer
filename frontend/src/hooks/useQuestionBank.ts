import { useState, useEffect, useCallback, useMemo } from "react";
import { toast } from "sonner";
import type { Question, QuestionFormData } from "@/types/question";
import { emptyQuestionForm } from "@/types/question";
import * as api from "@/lib/api";

export interface QuestionFilters {
  searchTerm: string;
  typeFilter: string;
  tagFilter: string;
  difficultyFilter: string;
  showStarredOnly: boolean;
  sortBy: string;
}

export interface UseQuestionBankReturn {
  questions: Question[];
  loading: boolean;
  filters: QuestionFilters;
  setFilters: React.Dispatch<React.SetStateAction<QuestionFilters>>;
  filteredQuestions: Question[];
  allTags: string[];
  
  selectedIds: Set<string>;
  setSelectedIds: React.Dispatch<React.SetStateAction<Set<string>>>;
  handleSelectAll: () => void;
  handleSelectOne: (id: string) => void;
  
  formData: QuestionFormData;
  setFormData: React.Dispatch<React.SetStateAction<QuestionFormData>>;
  editingQuestion: Question | null;
  setEditingQuestion: React.Dispatch<React.SetStateAction<Question | null>>;
  saving: boolean;
  
  fetchQuestions: () => Promise<void>;
  handleCreate: () => Promise<boolean>;
  handleUpdate: () => Promise<boolean>;
  handleDelete: () => Promise<boolean>;
  handleBulkDelete: () => Promise<boolean>;
  handleImport: (jsonData: string) => Promise<boolean>;
  handleExport: () => void;
  
  generateAnswer: (questionId: string) => Promise<void>;
  generateTags: (questionId: string) => Promise<void>;
  toggleStar: (questionId: string) => Promise<void>;
  
  generatingIds: Set<string>;
  taggingIds: Set<string>;
  
  expandedAnswers: Set<string>;
  setExpandedAnswers: React.Dispatch<React.SetStateAction<Set<string>>>;
  
  openAddDialog: () => void;
  openEditDialog: (question: Question) => void;
}

const defaultFilters: QuestionFilters = {
  searchTerm: "",
  typeFilter: "all",
  tagFilter: "all",
  difficultyFilter: "all",
  showStarredOnly: false,
  sortBy: "id",
};

export function useQuestionBank(): UseQuestionBankReturn {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<QuestionFilters>(defaultFilters);
  
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [formData, setFormData] = useState<QuestionFormData>(emptyQuestionForm);
  const [editingQuestion, setEditingQuestion] = useState<Question | null>(null);
  const [saving, setSaving] = useState(false);
  
  const [generatingIds, setGeneratingIds] = useState<Set<string>>(new Set());
  const [taggingIds, setTaggingIds] = useState<Set<string>>(new Set());
  const [expandedAnswers, setExpandedAnswers] = useState<Set<string>>(new Set());

  const allTags = useMemo(() => 
    Array.from(new Set(questions.flatMap(q => q.tags || []))).sort(),
    [questions]
  );

  const filteredQuestions = useMemo(() => {
    const { searchTerm, typeFilter, tagFilter, difficultyFilter, showStarredOnly, sortBy } = filters;
    
    return questions.filter(q => {
      const matchesSearch = q.content.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = typeFilter === "all" || q.type === typeFilter;
      const matchesTag = tagFilter === "all" || (q.tags && q.tags.includes(tagFilter));
      const matchesDifficulty = difficultyFilter === "all" || q.difficulty === difficultyFilter;
      const matchesStarred = !showStarredOnly || q.starred;
      return matchesSearch && matchesType && matchesTag && matchesDifficulty && matchesStarred;
    }).sort((a, b) => {
      switch (sortBy) {
        case "id": return a.id.localeCompare(b.id);
        case "id-desc": return b.id.localeCompare(a.id);
        case "difficulty": {
          const order = { easy: 1, medium: 2, hard: 3 };
          return (order[a.difficulty as keyof typeof order] || 0) - (order[b.difficulty as keyof typeof order] || 0);
        }
        case "difficulty-desc": {
          const order = { easy: 1, medium: 2, hard: 3 };
          return (order[b.difficulty as keyof typeof order] || 0) - (order[a.difficulty as keyof typeof order] || 0);
        }
        default: return 0;
      }
    });
  }, [questions, filters]);

  const fetchQuestions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.fetchQuestions();
      setQuestions(data);
    } catch (error) {
      console.error(error);
      toast.error("加载题库失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQuestions();
  }, [fetchQuestions]);

  const handleSelectAll = useCallback(() => {
    const filteredIds = new Set(filteredQuestions.map(q => q.id));
    const allSelected = filteredQuestions.length > 0 && 
      filteredQuestions.every(q => selectedIds.has(q.id));
    
    setSelectedIds(allSelected ? new Set() : filteredIds);
  }, [filteredQuestions, selectedIds]);

  const handleSelectOne = useCallback((id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const openAddDialog = useCallback(() => {
    setFormData({ ...emptyQuestionForm, options: ["", "", "", ""] });
  }, []);

  const openEditDialog = useCallback((question: Question) => {
    setEditingQuestion(question);
    setFormData({
      content: question.content,
      type: question.type,
      options: question.options || ["", "", "", ""],
      difficulty: question.difficulty || "medium",
      tags: question.tags || [],
      answer: question.answer || "",
      analysis: question.analysis || "",
      sub_questions: question.sub_questions || [],
    });
  }, []);

  const handleCreate = useCallback(async (): Promise<boolean> => {
    if (!formData.content.trim()) {
      toast.error("题目内容不能为空");
      return false;
    }
    
    setSaving(true);
    try {
      const payload: QuestionFormData = {
        content: formData.content,
        type: formData.type,
      };
      
      if (formData.type === "single_choice" || formData.type === "multiple_choice") {
        payload.options = formData.options?.filter(o => o.trim()) || [];
      }
      if (formData.difficulty) payload.difficulty = formData.difficulty;
      if (formData.tags?.length) payload.tags = formData.tags;
      if (formData.answer) payload.answer = formData.answer;
      if (formData.analysis) payload.analysis = formData.analysis;
      if (formData.sub_questions !== undefined) payload.sub_questions = formData.sub_questions;

      await api.createQuestion(payload);
      toast.success("题目创建成功");
      fetchQuestions();
      return true;
    } catch (error: unknown) {
      toast.error((error as Error).message);
      return false;
    } finally {
      setSaving(false);
    }
  }, [formData, fetchQuestions]);

  const handleUpdate = useCallback(async (): Promise<boolean> => {
    if (!editingQuestion || !formData.content.trim()) {
      toast.error("题目内容不能为空");
      return false;
    }
    
    setSaving(true);
    try {
      const payload: QuestionFormData = {
        content: formData.content,
        type: formData.type,
      };
      
      if (formData.type === "single_choice" || formData.type === "multiple_choice") {
        payload.options = formData.options?.filter(o => o.trim()) || [];
      }
      if (formData.difficulty) payload.difficulty = formData.difficulty;
      if (formData.tags?.length) payload.tags = formData.tags;
      if (formData.answer) payload.answer = formData.answer;
      if (formData.analysis) payload.analysis = formData.analysis;
      if (formData.sub_questions !== undefined) payload.sub_questions = formData.sub_questions;

      await api.updateQuestion(editingQuestion.id, payload);
      toast.success("题目更新成功");
      setEditingQuestion(null);
      fetchQuestions();
      return true;
    } catch (error: unknown) {
      toast.error((error as Error).message);
      return false;
    } finally {
      setSaving(false);
    }
  }, [editingQuestion, formData, fetchQuestions]);

  const handleDelete = useCallback(async (): Promise<boolean> => {
    if (!editingQuestion) return false;
    
    setSaving(true);
    try {
      await api.deleteQuestion(editingQuestion.id);
      toast.success("题目已删除");
      setEditingQuestion(null);
      fetchQuestions();
      return true;
    } catch (error: unknown) {
      toast.error((error as Error).message);
      return false;
    } finally {
      setSaving(false);
    }
  }, [editingQuestion, fetchQuestions]);

  const handleBulkDelete = useCallback(async (): Promise<boolean> => {
    if (selectedIds.size === 0) return false;
    
    setSaving(true);
    try {
      const result = await api.bulkDeleteQuestions(Array.from(selectedIds));
      toast.success(`已删除 ${result.deleted} 道题目`);
      setSelectedIds(new Set());
      fetchQuestions();
      return true;
    } catch (error: unknown) {
      toast.error((error as Error).message);
      return false;
    } finally {
      setSaving(false);
    }
  }, [selectedIds, fetchQuestions]);

  const handleImport = useCallback(async (jsonData: string): Promise<boolean> => {
    if (!jsonData.trim()) {
      toast.error("请输入JSON数据");
      return false;
    }
    
    setSaving(true);
    try {
      const result = await api.importQuestions(jsonData);
      toast.success(result.message);
      fetchQuestions();
      return true;
    } catch (error: unknown) {
      toast.error((error as Error).message);
      return false;
    } finally {
      setSaving(false);
    }
  }, [fetchQuestions]);

  const handleExport = useCallback(() => {
    const toExport = selectedIds.size > 0 
      ? questions.filter(q => selectedIds.has(q.id))
      : questions;
    
    const exportData = {
      meta: { subject: "Math", exported_at: new Date().toISOString() },
      questions: toExport,
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `question_bank_${new Date().toISOString().split("T")[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
    
    toast.success(`已导出 ${toExport.length} 道题目`);
  }, [questions, selectedIds]);

  const generateAnswer = useCallback(async (questionId: string) => {
    setGeneratingIds(prev => new Set(prev).add(questionId));
    try {
      const data = await api.generateAnswer(questionId);
      if (data.success) {
        toast.success("答案生成成功");
        setQuestions(prev => prev.map(q => 
          q.id === questionId 
            ? { ...q, answer: data.answer, analysis: data.analysis }
            : q
        ));
        setExpandedAnswers(prev => new Set(prev).add(questionId));
      } else {
        toast.error(data.message || "生成失败");
      }
    } catch (error) {
      console.error(error);
      toast.error("生成答案失败");
    } finally {
      setGeneratingIds(prev => {
        const next = new Set(prev);
        next.delete(questionId);
        return next;
      });
    }
  }, []);

  const generateTags = useCallback(async (questionId: string) => {
    setTaggingIds(prev => new Set(prev).add(questionId));
    try {
      const data = await api.generateTags(questionId);
      if (data.success) {
        toast.success(data.message || "标签生成成功");
        setQuestions(prev => prev.map(q => 
          q.id === questionId 
            ? { ...q, tags: data.tags, ...(data.difficulty && { difficulty: data.difficulty }) }
            : q
        ));
      } else {
        toast.error(data.message || "生成失败");
      }
    } catch (error) {
      console.error(error);
      toast.error("生成标签失败");
    } finally {
      setTaggingIds(prev => {
        const next = new Set(prev);
        next.delete(questionId);
        return next;
      });
    }
  }, []);

  const toggleStar = useCallback(async (questionId: string) => {
    const question = questions.find(q => q.id === questionId);
    if (!question) return;
    
    const newStarred = !question.starred;
    
    setQuestions(prev => prev.map(q => 
      q.id === questionId ? { ...q, starred: newStarred } : q
    ));
    
    try {
      await api.updateQuestion(questionId, { starred: newStarred });
    } catch (error) {
      setQuestions(prev => prev.map(q => 
        q.id === questionId ? { ...q, starred: !newStarred } : q
      ));
      console.error(error);
      toast.error("更新收藏状态失败");
    }
  }, [questions]);

  return {
    questions,
    loading,
    filters,
    setFilters,
    filteredQuestions,
    allTags,
    
    selectedIds,
    setSelectedIds,
    handleSelectAll,
    handleSelectOne,
    
    formData,
    setFormData,
    editingQuestion,
    setEditingQuestion,
    saving,
    
    fetchQuestions,
    handleCreate,
    handleUpdate,
    handleDelete,
    handleBulkDelete,
    handleImport,
    handleExport,
    
    generateAnswer,
    generateTags,
    toggleStar,
    
    generatingIds,
    taggingIds,
    
    expandedAnswers,
    setExpandedAnswers,
    
    openAddDialog,
    openEditDialog,
  };
}
