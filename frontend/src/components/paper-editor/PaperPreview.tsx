import { Button } from "@/components/ui/button";
import { FileText, Eye, Trash2 } from "lucide-react";
import type { Section, PaperConfig } from "@/types/paper-editor";
import { SectionComponent } from "./SectionComponent";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { cn } from "@/lib/utils";
import { getBadgeClass, getTypeLabel } from "@/lib/paper-editor-constants";
import { Badge } from "@/components/ui/badge";
import { useDroppable } from "@dnd-kit/core";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";

interface PaperPreviewProps {
  sections: Section[];
  paperConfig: PaperConfig;
  totalScore: number;
  previewOpen: boolean;
  selectedQuestionId: string | null;
  onSelectQuestion: (id: string) => void;
  onRemoveQuestion: (sectionIndex: number, questionId: string) => void;
  onScoreChange: (sectionIndex: number, questionId: string, score: number) => void;
  onTitleChange: (sectionIndex: number, title: string) => void;
  onClearSelection: () => void;
  onOpenPreview: () => void;
}

export function PaperPreview({
  sections,
  paperConfig,
  totalScore,
  previewOpen,
  selectedQuestionId,
  onSelectQuestion,
  onRemoveQuestion,
  onScoreChange,
  onTitleChange,
  onClearSelection,
  onOpenPreview,
}: PaperPreviewProps) {
  const totalQuestions = sections.reduce((sum, s) => sum + s.questions.length, 0);
  
  const { setNodeRef, isOver } = useDroppable({
    id: "paper-drop-zone",
    data: { type: "paper-drop-zone" },
  });

  return (
    <div
      ref={setNodeRef}
      className={cn(
        "flex-1 overflow-y-auto p-6 flex justify-center",
        isOver && "bg-primary/5"
      )}
      onClick={onClearSelection}
    >
      {sections.length === 0 ? (
        <div className={cn(
          "w-full max-w-2xl min-h-[300px] bg-background border-2 border-dashed rounded-xl flex flex-col items-center justify-center text-muted-foreground/40 select-none transition-colors",
          isOver ? "border-primary/50 bg-primary/5" : "border-border/30"
        )}>
          <div className="p-6 rounded-full bg-muted/30 mb-4">
            <FileText className="h-12 w-12" />
          </div>
          <p className="text-lg font-medium mb-1">空白试卷</p>
          <p className="text-sm max-w-xs text-center">
            从左侧题库拖拽题目到此处，或点击 + 按钮添加
          </p>
        </div>
      ) : !previewOpen ? (
        <div className="w-full max-w-3xl space-y-3">
          <div className="flex items-center justify-between bg-background/90 backdrop-blur-sm sticky top-0 z-10 py-3 px-4 rounded-lg border border-border/40 shadow-sm">
            <div className="flex items-center gap-3">
              <h2 className="font-bold">{paperConfig.title || "未命名试卷"}</h2>
              <span className="text-sm text-muted-foreground">
                {totalQuestions} 题 · {totalScore} 分
              </span>
            </div>
            <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); onOpenPreview(); }}>
              <Eye className="h-4 w-4 mr-1.5" />
              预览
            </Button>
          </div>

          {sections.map((section, sectionIdx) => (
            <div key={section.id} className="bg-background rounded-lg border border-border/40 overflow-hidden">
              <div className="px-4 py-2.5 bg-muted/30 border-b border-border/30 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className={cn("text-[10px] h-5", getBadgeClass(section.type))}>
                    {getTypeLabel(section.type)}
                  </Badge>
                  <input
                    value={section.title}
                    onChange={(e) => onTitleChange(sectionIdx, e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="font-medium text-sm bg-transparent border-none outline-none hover:text-primary focus:text-primary"
                  />
                </div>
                <span className="text-xs text-muted-foreground">
                  {section.questions.length} 题 · {section.questions.reduce((sum, q) => sum + q.score, 0)} 分
                </span>
              </div>

              <SortableContext
                items={section.questions.map((q) => q.id)}
                strategy={verticalListSortingStrategy}
              >
                <div className="divide-y divide-border/20">
                  {section.questions.map((question, qIdx) => (
                    <div
                      key={question.id}
                      onClick={(e) => { e.stopPropagation(); onSelectQuestion(question.id); }}
                      className={cn(
                        "group flex items-center gap-3 px-4 py-2.5 transition-colors cursor-pointer",
                        selectedQuestionId === question.id
                          ? "bg-primary/5"
                          : "hover:bg-muted/30"
                      )}
                    >
                      <span className="text-sm font-medium text-muted-foreground w-6 shrink-0">
                        {qIdx + 1}.
                      </span>

                      <div className="flex-1 text-sm text-foreground/80 truncate [&_p]:inline [&_.katex]:text-[0.85em]">
                        <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                          {question.content.length > 100 
                            ? question.content.substring(0, 100) + '...' 
                            : question.content}
                        </ReactMarkdown>
                      </div>

                      <div className="flex items-center gap-1.5 shrink-0">
                        <input
                          type="number"
                          value={question.score}
                          onChange={(e) => {
                            e.stopPropagation();
                            onScoreChange(sectionIdx, question.id, parseInt(e.target.value) || 0);
                          }}
                          onClick={(e) => e.stopPropagation()}
                          className="w-10 h-6 text-center text-xs bg-muted/50 border border-border/50 rounded focus:ring-1 focus:ring-primary outline-none"
                          min={0}
                        />
                        <span className="text-xs text-muted-foreground">分</span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onRemoveQuestion(sectionIdx, question.id);
                          }}
                          className="p-1 text-muted-foreground hover:text-destructive rounded hover:bg-destructive/10 opacity-0 group-hover:opacity-100 transition-all"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </SortableContext>
            </div>
          ))}
        </div>
      ) : (
        <div className="w-full max-w-4xl space-y-6 pb-8">
          <div className="text-center py-6 border-b border-border/50">
            <h1 className="text-2xl font-bold mb-2">
              {paperConfig.title || "未命名试卷"}
            </h1>
            <div className="flex items-center justify-center gap-4 text-sm text-muted-foreground">
              <span>科目：{paperConfig.subject}</span>
              <span>时间：{paperConfig.duration}分钟</span>
              <span>满分：{totalScore}分</span>
            </div>
          </div>

          <div className="space-y-6">
            {sections.map((section, idx) => (
              <SectionComponent
                key={section.id}
                section={section}
                sectionIndex={idx}
                onRemoveQuestion={(qId) => onRemoveQuestion(idx, qId)}
                onScoreChange={(qId, score) => onScoreChange(idx, qId, score)}
                onTitleChange={(title) => onTitleChange(idx, title)}
                selectedQuestionId={selectedQuestionId}
                onSelectQuestion={onSelectQuestion}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
