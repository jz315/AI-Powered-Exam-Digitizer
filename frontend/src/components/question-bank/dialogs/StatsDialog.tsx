import { Button } from "@/components/ui/button";
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { BarChart3 } from "lucide-react";
import type { Question } from "@/types/question";
import { QUESTION_TYPES, DIFFICULTIES } from "@/lib/constants";

interface StatsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  questions: Question[];
}

export function StatsDialog({
  open,
  onOpenChange,
  questions,
}: StatsDialogProps) {
  const typeStats = QUESTION_TYPES.map(t => ({
    ...t,
    count: questions.filter(q => q.type === t.value).length,
  }));

  const difficultyStats = DIFFICULTIES.map(d => ({
    ...d,
    count: questions.filter(q => q.difficulty === d.value).length,
  }));

  const tagStats = questions
    .flatMap(q => q.tags || [])
    .reduce((acc, tag) => {
      acc[tag] = (acc[tag] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

  const topTags = Object.entries(tagStats)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent onClose={() => onOpenChange(false)} className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5 text-primary" /> 题库统计
          </DialogTitle>
          <DialogDescription>
            共 {questions.length} 道题目
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          <div>
            <h4 className="text-sm font-medium mb-3">按题型</h4>
            <div className="grid grid-cols-2 gap-2">
              {typeStats.map(t => (
                <div key={t.value} className="flex items-center justify-between p-2 bg-muted/30 rounded-lg">
                  <span className="text-sm">{t.label}</span>
                  <span className="text-sm font-bold text-primary">{t.count}</span>
                </div>
              ))}
            </div>
          </div>

          <div>
            <h4 className="text-sm font-medium mb-3">按难度</h4>
            <div className="grid grid-cols-3 gap-2">
              {difficultyStats.map(d => (
                <div key={d.value} className="flex items-center justify-between p-2 bg-muted/30 rounded-lg">
                  <span className="text-sm">{d.label}</span>
                  <span className="text-sm font-bold text-primary">{d.count}</span>
                </div>
              ))}
            </div>
          </div>

          {topTags.length > 0 && (
            <div>
              <h4 className="text-sm font-medium mb-3">热门标签</h4>
              <div className="flex flex-wrap gap-2">
                {topTags.map(([tag, count]) => (
                  <div key={tag} className="px-2 py-1 bg-muted/30 rounded-full text-xs">
                    {tag} <span className="text-primary font-bold">({count})</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
