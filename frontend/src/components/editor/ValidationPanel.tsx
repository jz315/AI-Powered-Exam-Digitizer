import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Play,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ValidationIssue, ValidationStatus } from "@/types/editor";

interface ValidationPanelProps {
  issues: ValidationIssue[];
  validationStatus: ValidationStatus;
  isValidating: boolean;
  errorCount: number;
  warningCount: number;
  onValidate: () => void;
  onIssueClick: (line: number) => void;
}

export function ValidationPanel({
  issues,
  validationStatus,
  isValidating,
  errorCount,
  warningCount,
  onValidate,
  onIssueClick,
}: ValidationPanelProps) {
  return (
    <Card className="glass-card">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Play className="h-4 w-4 text-accent" />
          验证结果
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button 
          className={cn(
            "w-full",
            validationStatus === "valid" ? "hover-lift" : "btn-primary-gradient"
          )}
          onClick={onValidate}
          variant={validationStatus === "valid" ? "outline" : "default"}
          disabled={isValidating}
        >
          {isValidating ? (
            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> 验证中...</>
          ) : (
            <><Play className="mr-2 h-4 w-4" /> 运行验证</>
          )}
        </Button>

        <div className="space-y-2">
          {issues.length === 0 && validationStatus === "valid" ? (
            <Alert className="border-success/50 bg-success/10 text-success animate-fade-in">
              <CheckCircle2 className="h-4 w-4" />
              <AlertTitle>所有检查通过</AlertTitle>
              <AlertDescription>
                JSON结构有效且符合规范，可以导入题库。
              </AlertDescription>
            </Alert>
          ) : issues.length > 0 ? (
            <div className="space-y-2 animate-fade-in">
              <div className="flex items-center gap-3 text-sm font-medium">
                {errorCount > 0 && (
                  <span className="flex items-center gap-1 text-destructive">
                    <AlertCircle className="h-4 w-4" />
                    {errorCount} 个错误
                  </span>
                )}
                {warningCount > 0 && (
                  <span className="flex items-center gap-1 text-warning">
                    <AlertTriangle className="h-4 w-4" />
                    {warningCount} 个警告
                  </span>
                )}
              </div>
              <div className="max-h-48 overflow-y-auto space-y-2">
                {issues.map((issue, idx) => (
                  <div
                    key={idx}
                    onClick={() => onIssueClick(issue.line)}
                    className={cn(
                      "p-2 rounded-lg cursor-pointer transition-colors text-xs",
                      issue.severity === "error" 
                        ? "bg-destructive/10 hover:bg-destructive/20 text-destructive border border-destructive/30"
                        : "bg-warning/10 hover:bg-warning/20 text-warning border border-warning/30"
                    )}
                  >
                    <div className="flex items-start gap-2">
                      {issue.severity === "error" ? (
                        <AlertCircle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                      ) : (
                        <AlertTriangle className="h-3.5 w-3.5 mt-0.5 flex-shrink-0" />
                      )}
                      <div>
                        <span className="font-mono font-medium">
                          {issue.line > 0 ? `第${issue.line}行: ` : ""}
                        </span>
                        <span>{issue.message}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-sm text-muted-foreground text-center py-8">
              编辑内容后自动验证，或点击"运行验证"手动检查。
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
