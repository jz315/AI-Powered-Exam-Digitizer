import { useState, useEffect, useMemo, useCallback } from "react";
import type { DragEndEvent, DragStartEvent } from "@dnd-kit/core";
import { toast } from "sonner";
import type { Question, PaperQuestion, Section, PaperConfig } from "@/types/paper-editor";
import {
  API_BASE,
  DEFAULT_SCORES,
  DEFAULT_PAPER_CONFIG,
  getSectionTitle,
} from "@/lib/paper-editor-constants";
import { usePaperCart } from "@/contexts/PaperCartContext";

export function usePaperEditor() {
  const [bankQuestions, setBankQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const [sections, setSections] = useState<Section[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [selectedQuestionId, setSelectedQuestionId] = useState<string | null>(null);
  const [previewOpen, setPreviewOpen] = useState(false);

  const [paperConfig, setPaperConfig] = useState<PaperConfig>(DEFAULT_PAPER_CONFIG);
  const [generatingPaper, setGeneratingPaper] = useState(false);
  
  const { cartItems } = usePaperCart();

  useEffect(() => {
    fetchQuestions();
  }, []);

  const fetchQuestions = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/questions`);
      if (!response.ok) throw new Error("加载题库失败");
      const data = await response.json();
      setBankQuestions(data.questions || []);
    } catch (error) {
      console.error(error);
      toast.error("加载题库失败");
    } finally {
      setLoading(false);
    }
  };

  const initializeSectionsFromCart = useCallback(() => {
    const grouped: Record<string, PaperQuestion[]> = {};
    cartItems.forEach((item) => {
      const type = item.type || "problem";
      if (!grouped[type]) grouped[type] = [];
      grouped[type].push({ ...item, score: DEFAULT_SCORES[type] || 5 });
    });

    const typeOrder = ["single_choice", "multiple_choice", "fill", "problem"];
    const newSections: Section[] = [];
    let sectionIdx = 0;

    typeOrder.forEach((type) => {
      if (grouped[type] && grouped[type].length > 0) {
        newSections.push({
          id: `section-${type}-${Date.now()}`,
          title: getSectionTitle(type, sectionIdx),
          type,
          questions: grouped[type],
        });
        sectionIdx++;
      }
    });
    setSections(newSections);
  }, [cartItems]);

  const importFromCart = useCallback(() => {
    if (cartItems.length === 0) {
      toast.info("试卷篮为空");
      return;
    }
    if (sections.length > 0) {
      toast.info("当前试卷已有内容，请先清空再导入");
      return;
    }
    initializeSectionsFromCart();
    setPreviewOpen(true);
  }, [cartItems.length, sections.length, initializeSectionsFromCart]);

  const paperQuestionIds = useMemo(() => {
    const ids = new Set<string>();
    sections.forEach((s) => s.questions.forEach((q) => ids.add(q.id)));
    return ids;
  }, [sections]);

  const filteredQuestions = useMemo(() => {
    return bankQuestions.filter((q) => {
      const matchesSearch =
        q.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
        q.id.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesType = typeFilter === "all" || q.type === typeFilter;
      return matchesSearch && matchesType;
    });
  }, [bankQuestions, searchTerm, typeFilter]);

  const totalScore = useMemo(() => {
    return sections.reduce(
      (sum, s) => sum + s.questions.reduce((qSum, q) => qSum + q.score, 0),
      0
    );
  }, [sections]);

  const totalQuestions = useMemo(() => {
    return sections.reduce((sum, s) => sum + s.questions.length, 0);
  }, [sections]);

  const addQuestionToPaper = useCallback(
    (question: Question) => {
      if (paperQuestionIds.has(question.id)) {
        toast.info("该题目已在试卷中");
        return;
      }

      const type = question.type || "problem";
      const paperQuestion: PaperQuestion = {
        ...question,
        score: DEFAULT_SCORES[type] || 5,
      };

      const existingSectionIdx = sections.findIndex((s) => s.type === type);

      if (existingSectionIdx >= 0) {
        setSections((prev) =>
          prev.map((s, idx) =>
            idx === existingSectionIdx
              ? { ...s, questions: [...s.questions, paperQuestion] }
              : s
          )
        );
      } else {
        const newSection: Section = {
          id: `section-${type}-${Date.now()}`,
          title: getSectionTitle(type, sections.length),
          type,
          questions: [paperQuestion],
        };
        setSections((prev) => [...prev, newSection]);
      }

      toast.success("已添加到试卷");
    },
    [paperQuestionIds, sections]
  );

  const removeQuestion = useCallback(
    (sectionIndex: number, questionId: string) => {
      setSections((prev) => {
        const newSections = prev.map((s, idx) => {
          if (idx !== sectionIndex) return s;
          return { ...s, questions: s.questions.filter((q) => q.id !== questionId) };
        });
        return newSections.filter((s) => s.questions.length > 0);
      });
      if (selectedQuestionId === questionId) setSelectedQuestionId(null);
    },
    [selectedQuestionId]
  );

  const updateQuestionScore = useCallback(
    (sectionIndex: number, questionId: string, score: number) => {
      setSections((prev) =>
        prev.map((s, idx) => {
          if (idx !== sectionIndex) return s;
          return {
            ...s,
            questions: s.questions.map((q) =>
              q.id === questionId ? { ...q, score } : q
            ),
          };
        })
      );
    },
    []
  );

  const updateSectionTitle = useCallback((sectionIndex: number, title: string) => {
    setSections((prev) =>
      prev.map((s, i) => (i === sectionIndex ? { ...s, title } : s))
    );
  }, []);

  const clearSections = useCallback(() => {
    setSections([]);
    toast.success("试卷已清空");
  }, []);

  const generatePDF = async () => {
    if (sections.length === 0) {
      toast.error("请先添加题目到试卷");
      return;
    }
    setGeneratingPaper(true);
    try {
      const response = await fetch(`${API_BASE}/api/paper/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sections: sections.map((s) => ({
            title: s.title,
            type: s.type,
            questions: s.questions,
          })),
          subject: paperConfig.subject,
          title: paperConfig.title,
          school: paperConfig.school,
          exam_time: paperConfig.examTime,
          duration: paperConfig.duration,
        }),
      });

      const data = await response.json();
      if (data.success && data.pdf_path) {
        toast.success("生成成功！");
        const pdfUrl = `${API_BASE}/output/question_bank/generated/${data.pdf_path.split(/[/\\]/).pop()}`;
        window.open(pdfUrl, "_blank");
      } else {
        toast.error(data.message || "生成失败");
      }
    } catch (error) {
      console.error(error);
      toast.error("生成试卷失败");
    } finally {
      setGeneratingPaper(false);
    }
  };

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as string);
  }, []);

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveId(null);
      if (!over) return;

      const activeData = active.data.current;
      const overData = over.data.current;

      if (activeData?.type === "bank-question") {
        const question = activeData.question as Question;
        addQuestionToPaper(question);
        return;
      }

      if (activeData?.type === "paper-question" && active.id !== over.id) {
        const activeSectionIdx = activeData.sectionIndex as number;
        let targetSectionIdx = activeSectionIdx;
        let targetPosition = 0;

        if (overData?.type === "paper-question") {
          targetSectionIdx = overData.sectionIndex as number;
          const targetSection = sections[targetSectionIdx];
          targetPosition = targetSection.questions.findIndex((q) => q.id === over.id);
        } else if (overData?.type === "section") {
          targetSectionIdx = overData.sectionIndex as number;
          targetPosition = sections[targetSectionIdx].questions.length;
        }

        if (activeSectionIdx === targetSectionIdx) {
          setSections((prev) =>
            prev.map((s, idx) => {
              if (idx !== activeSectionIdx) return s;
              const questions = [...s.questions];
              const oldIdx = questions.findIndex((q) => q.id === active.id);
              const [removed] = questions.splice(oldIdx, 1);
              questions.splice(targetPosition, 0, removed);
              return { ...s, questions };
            })
          );
        } else {
          const question = sections[activeSectionIdx].questions.find(
            (q) => q.id === active.id
          );
          if (!question) return;

          const targetSectionType = sections[targetSectionIdx].type;
          const newScore = DEFAULT_SCORES[targetSectionType] || question.score;

          setSections((prev) => {
            const newSections = prev.map((s, idx) => {
              if (idx === activeSectionIdx) {
                return { ...s, questions: s.questions.filter((q) => q.id !== active.id) };
              }
              if (idx === targetSectionIdx) {
                const questions = [...s.questions];
                questions.splice(targetPosition, 0, { ...question, score: newScore });
                return { ...s, questions };
              }
              return s;
            });
            return newSections.filter((s) => s.questions.length > 0);
          });
        }
      }
    },
    [addQuestionToPaper, sections]
  );

  const getSelectedQuestion = useCallback((): PaperQuestion | null => {
    if (!selectedQuestionId) return null;
    for (const section of sections) {
      const q = section.questions.find((q) => q.id === selectedQuestionId);
      if (q) return q;
    }
    return null;
  }, [selectedQuestionId, sections]);

  const selectedQuestion = getSelectedQuestion();

  const findSectionIndexByQuestionId = useCallback(
    (questionId: string): number => {
      return sections.findIndex((s) => s.questions.some((q) => q.id === questionId));
    },
    [sections]
  );

  return {
    bankQuestions,
    loading,
    searchTerm,
    setSearchTerm,
    typeFilter,
    setTypeFilter,
    sections,
    activeId,
    selectedQuestionId,
    setSelectedQuestionId,
    previewOpen,
    setPreviewOpen,
    paperConfig,
    setPaperConfig,
    generatingPaper,
    cartItems,
    paperQuestionIds,
    filteredQuestions,
    totalScore,
    totalQuestions,
    selectedQuestion,
    fetchQuestions,
    importFromCart,
    addQuestionToPaper,
    removeQuestion,
    updateQuestionScore,
    updateSectionTitle,
    clearSections,
    generatePDF,
    handleDragStart,
    handleDragEnd,
    findSectionIndexByQuestionId,
  };
}
