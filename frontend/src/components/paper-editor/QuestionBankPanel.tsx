import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Search, RefreshCw, BookOpen, LayoutTemplate } from "lucide-react";
import { cn } from "@/lib/utils";
import type { Question } from "@/types/paper-editor";
import { QUESTION_TYPES } from "@/lib/paper-editor-constants";
import { DraggableQuestionCard } from "./DraggableQuestionCard";

interface QuestionBankPanelProps {
  questions: Question[];
  loading: boolean;
  searchTerm: string;
  onSearchChange: (term: string) => void;
  typeFilter: string;
  onTypeFilterChange: (type: string) => void;
  paperQuestionIds: Set<string>;
  onAddQuestion: (question: Question) => void;
  onRefresh: () => void;
}

export function QuestionBankPanel({
  questions,
  loading,
  searchTerm,
  onSearchChange,
  typeFilter,
  onTypeFilterChange,
  paperQuestionIds,
  onAddQuestion,
  onRefresh,
}: QuestionBankPanelProps) {
  return (
    <div className="w-72 shrink-0 border-r border-border/50 bg-background/50 flex flex-col z-10 backdrop-blur-sm">
      <div className="p-5 border-b border-border/50">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 rounded-xl bg-primary/10 text-primary">
            <LayoutTemplate className="h-5 w-5" />
          </div>
          <h2 className="font-bold text-lg">题库资源</h2>
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="搜索题目内容..."
            className="pl-9 h-10 bg-muted/30 border-border/50 focus:bg-background transition-colors"
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </div>
      </div>

      <div className="px-5 py-3 flex gap-2 overflow-x-auto no-scrollbar border-b border-border/50">
        <button
          onClick={() => onTypeFilterChange("all")}
          className={cn(
            "px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all",
            typeFilter === "all"
              ? "bg-primary text-primary-foreground shadow-sm"
              : "bg-muted/50 text-muted-foreground hover:bg-muted"
          )}
        >
          全部
        </button>
        {QUESTION_TYPES.map((type) => (
          <button
            key={type.value}
            onClick={() => onTypeFilterChange(type.value)}
            className={cn(
              "px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all",
              typeFilter === type.value
                ? "bg-primary text-primary-foreground shadow-sm"
                : "bg-muted/50 text-muted-foreground hover:bg-muted"
            )}
          >
            {type.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-10 text-muted-foreground space-y-3">
            <RefreshCw className="h-6 w-6 animate-spin text-primary" />
            <span className="text-sm">正在同步题库...</span>
          </div>
        ) : questions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-muted-foreground opacity-50">
            <BookOpen className="h-10 w-10 mb-3 stroke-1" />
            <span className="text-sm">暂无匹配题目</span>
          </div>
        ) : (
          <SortableContext
            items={questions.map((q) => `bank-${q.id}`)}
            strategy={verticalListSortingStrategy}
          >
            {questions.map((q) => (
              <DraggableQuestionCard
                key={q.id}
                question={q}
                onAdd={() => onAddQuestion(q)}
                isInPaper={paperQuestionIds.has(q.id)}
              />
            ))}
          </SortableContext>
        )}
      </div>

      <div className="p-4 border-t border-border/50 bg-muted/10">
        <Button
          variant="ghost"
          size="sm"
          className="w-full text-muted-foreground hover:text-primary"
          onClick={onRefresh}
        >
          <RefreshCw className="h-3 w-3 mr-2" /> 刷新题库
        </Button>
      </div>
    </div>
  );
}
