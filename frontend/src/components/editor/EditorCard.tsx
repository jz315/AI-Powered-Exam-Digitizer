import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { LazyMonacoEditor } from "@/components/LazyMonacoEditor";
import type { OnMount } from "@monaco-editor/react";
import { FileJson, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import type { ValidationStatus } from "@/types/editor";

interface EditorCardProps {
  code: string;
  validationStatus: ValidationStatus;
  isValidating: boolean;
  errorCount: number;
  warningCount: number;
  onCodeChange: (value: string) => void;
  onEditorMount: OnMount;
}

export function EditorCard({
  code,
  validationStatus,
  isValidating,
  errorCount,
  warningCount,
  onCodeChange,
  onEditorMount,
}: EditorCardProps) {
  return (
    <Card className="lg:col-span-2 flex flex-col overflow-hidden glass-card">
      <CardHeader className="py-2 px-4 border-b border-border/50 flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <FileJson className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium">data.json</span>
        </div>
        <div className="flex items-center gap-2">
          {isValidating && (
            <Badge variant="outline" className="animate-pulse">
              <Loader2 className="h-3 w-3 mr-1 animate-spin" /> 验证中...
            </Badge>
          )}
          {!isValidating && validationStatus === "valid" && (
            <Badge className="badge-gradient-green animate-scale-in">
              <CheckCircle2 className="h-3 w-3 mr-1" /> 有效
            </Badge>
          )}
          {!isValidating && validationStatus === "invalid" && (
            <Badge variant="destructive" className="animate-scale-in">
              <AlertCircle className="h-3 w-3 mr-1" /> 
              {errorCount > 0 ? `${errorCount}个错误` : "无效"}
              {warningCount > 0 && `, ${warningCount}个警告`}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="p-0 flex-1 relative monaco-container">
        <LazyMonacoEditor
          height="100%"
          defaultLanguage="json"
          theme="vs-dark"
          value={code}
          onChange={(value) => onCodeChange(value || "")}
          onMount={onEditorMount}
          options={{
            padding: { top: 16, bottom: 16 },
          }}
          fallbackHeight="400px"
        />
      </CardContent>
    </Card>
  );
}
