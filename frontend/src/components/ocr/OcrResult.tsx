import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { FileText, Copy, ExternalLink } from "lucide-react";

interface OcrResultProps {
  result: string;
  onCopy: () => void;
  onOpenEditor: () => void;
}

export function OcrResult({ result, onCopy, onOpenEditor }: OcrResultProps) {
  return (
    <Card className="flex-1 min-h-[300px] flex flex-col shadow-sm border-border/60">
      <CardHeader className="py-3 px-5 border-b bg-muted/10 flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-sm font-medium">识别结果</CardTitle>
        </div>
        <div className="flex gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={onCopy}
            disabled={!result}
            className="h-7 px-2 text-xs"
          >
            <Copy className="h-3.5 w-3.5 mr-1" /> 复制
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={!result}
            onClick={onOpenEditor}
            className="h-7 px-2 text-xs"
          >
            <ExternalLink className="h-3.5 w-3.5 mr-1" /> 编辑器
          </Button>
        </div>
      </CardHeader>
      <CardContent className="flex-1 p-0 relative">
        <textarea
          className="w-full h-full p-4 font-mono text-sm bg-transparent resize-none focus:outline-none"
          value={result}
          readOnly
          placeholder="等待识别结果..."
        />
      </CardContent>
    </Card>
  );
}
