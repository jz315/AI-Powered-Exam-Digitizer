import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Section } from "@/types/paper-editor";
import { SortablePaperQuestion } from "./SortablePaperQuestion";

interface SectionComponentProps {
  section: Section;
  sectionIndex: number;
  onRemoveQuestion: (questionId: string) => void;
  onScoreChange: (questionId: string, score: number) => void;
  onTitleChange: (title: string) => void;
  selectedQuestionId: string | null;
  onSelectQuestion: (id: string) => void;
}

export function SectionComponent({
  section,
  sectionIndex,
  onRemoveQuestion,
  onScoreChange,
  onTitleChange,
  selectedQuestionId,
  onSelectQuestion,
}: SectionComponentProps) {
  const { setNodeRef } = useDroppable({
    id: `section-${section.id}`,
    data: { type: "section", sectionIndex },
  });

  return (
    <div ref={setNodeRef} className="mb-8">
      <div className="flex items-baseline gap-3 mb-4 border-b border-border/40 pb-2 group">
        <input
          value={section.title}
          onChange={(e) => onTitleChange(e.target.value)}
          className="text-lg font-bold bg-transparent border-none outline-none hover:text-primary focus:text-primary transition-colors min-w-[200px]"
        />
        <span className="text-sm text-muted-foreground font-normal">
          (共 {section.questions.length} 题，合计{" "}
          {section.questions.reduce((sum, q) => sum + q.score, 0)} 分)
        </span>
      </div>

      <div className="space-y-1 min-h-[50px]">
        <SortableContext
          items={section.questions.map((q) => q.id)}
          strategy={verticalListSortingStrategy}
        >
          {section.questions.map((q, idx) => (
            <SortablePaperQuestion
              key={q.id}
              question={q}
              index={idx}
              sectionIndex={sectionIndex}
              onRemove={() => onRemoveQuestion(q.id)}
              onScoreChange={(score) => onScoreChange(q.id, score)}
              isSelected={selectedQuestionId === q.id}
              onSelect={() => onSelectQuestion(q.id)}
            />
          ))}
        </SortableContext>
        {section.questions.length === 0 && (
          <div className="h-20 border-2 border-dashed border-muted-foreground/10 rounded-lg flex items-center justify-center text-muted-foreground/40 text-sm">
            拖拽题目到此处
          </div>
        )}
      </div>
    </div>
  );
}
