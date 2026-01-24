import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileJson } from "lucide-react";

export function FormatGuidePanel() {
  return (
    <Card className="glass-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileJson className="h-4 w-4 text-primary" />
          格式指南
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-xs text-muted-foreground space-y-2 font-mono bg-muted/50 p-4 rounded-lg border border-border/50">
          <p><span className="text-primary">"type"</span>: "choice" | "problem" | "fill"</p>
          <p><span className="text-primary">"content"</span>: "题目内容..."</p>
          <p><span className="text-primary">"options"</span>: ["A", "B", "C", "D"]（选择题）</p>
          <p><span className="text-primary">"answer"</span>: "正确答案"</p>
          <p><span className="text-primary">"analysis"</span>: "解析说明..."</p>
          <p><span className="text-primary">"tags"</span>: ["标签1", "标签2"]</p>
          <p><span className="text-primary">"difficulty"</span>: "easy" | "medium" | "hard"</p>
        </div>
      </CardContent>
    </Card>
  );
}
