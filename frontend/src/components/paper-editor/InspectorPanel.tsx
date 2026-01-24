import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Settings2 } from "lucide-react";
import type { PaperQuestion, PaperConfig } from "@/types/paper-editor";
import { getTypeLabel } from "@/lib/paper-editor-constants";

interface InspectorPanelProps {
  config: PaperConfig;
  setConfig: (config: PaperConfig) => void;
  selectedQuestion: PaperQuestion | null;
  onUpdateScore: (score: number) => void;
  totalScore: number;
  questionCount: number;
}

export function InspectorPanel({
  config,
  setConfig,
  selectedQuestion,
  onUpdateScore,
  totalScore,
  questionCount,
}: InspectorPanelProps) {
  return (
    <div className="w-72 shrink-0 bg-background border-l border-border/50 flex flex-col h-full shadow-xl z-20">
      <div className="p-5 border-b border-border/50 flex items-center gap-2">
        <Settings2 className="h-4 w-4 text-primary" />
        <h3 className="font-semibold text-sm">属性配置</h3>
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {selectedQuestion ? (
          <div className="space-y-6 animate-in slide-in-from-right-4 duration-300">
            <div className="flex items-center justify-between">
              <h4 className="font-medium text-sm">题目属性</h4>
              <Badge variant="outline">{getTypeLabel(selectedQuestion.type)}</Badge>
            </div>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label>分值设置</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    value={selectedQuestion.score}
                    onChange={(e) => onUpdateScore(Number(e.target.value))}
                    className="w-24"
                    min={0}
                  />
                  <span className="text-sm text-muted-foreground">分</span>
                </div>
              </div>

              <div className="space-y-2">
                <Label>答案</Label>
                <div className="p-3 bg-muted/30 rounded-lg text-sm font-mono break-all border border-border/50">
                  {selectedQuestion.answer || "无答案"}
                </div>
              </div>

              <div className="space-y-2">
                <Label>解析</Label>
                <div className="p-3 bg-muted/30 rounded-lg text-sm text-muted-foreground max-h-40 overflow-y-auto border border-border/50">
                  <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                    {selectedQuestion.analysis || "无解析"}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="space-y-6 animate-in fade-in duration-300">
            <h4 className="font-medium text-sm">试卷设置</h4>

            <div className="space-y-4">
              <div className="space-y-2">
                <Label>主标题</Label>
                <Input
                  value={config.title}
                  onChange={(e) => setConfig({ ...config, title: e.target.value })}
                  placeholder="2024年高三模拟考试"
                />
              </div>

              <div className="space-y-2">
                <Label>副标题 / 科目</Label>
                <Input
                  value={config.subject}
                  onChange={(e) => setConfig({ ...config, subject: e.target.value })}
                  placeholder="数学"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>学校</Label>
                  <Input
                    value={config.school}
                    onChange={(e) => setConfig({ ...config, school: e.target.value })}
                    placeholder="XX中学"
                  />
                </div>
                <div className="space-y-2">
                  <Label>考试时间</Label>
                  <Input
                    value={config.examTime}
                    onChange={(e) => setConfig({ ...config, examTime: e.target.value })}
                    placeholder="2024.06"
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label>考试时长 (分钟)</Label>
                <Input
                  value={config.duration}
                  onChange={(e) => setConfig({ ...config, duration: e.target.value })}
                  placeholder="120"
                />
              </div>
            </div>

            <div className="pt-6 border-t border-border/50">
              <h4 className="font-medium text-sm mb-4">概览统计</h4>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-primary/5 rounded-lg border border-primary/10 text-center">
                  <div className="text-2xl font-bold text-primary">{totalScore}</div>
                  <div className="text-xs text-muted-foreground">总分</div>
                </div>
                <div className="p-3 bg-muted/50 rounded-lg border border-border/50 text-center">
                  <div className="text-2xl font-bold text-foreground">{questionCount}</div>
                  <div className="text-xs text-muted-foreground">题目数量</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
