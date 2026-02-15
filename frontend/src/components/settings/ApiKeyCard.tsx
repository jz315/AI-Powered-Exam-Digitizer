import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Eye, EyeOff, Save, Key, CheckCircle2, Loader2 } from "lucide-react";
import type { ApiKeyConfig, ApiKeysStatus, ApiKeyType } from "@/types/settings";

interface ApiKeyCardProps {
  config: ApiKeyConfig;
  apiKeysStatus: ApiKeysStatus;
  keyInput: string;
  savingKey: string | null;
  testing?: boolean;
  onKeyInputChange: (value: string) => void;
  onSave: () => void;
  onTest?: () => void;
}

export function ApiKeyCard({
  config,
  apiKeysStatus,
  keyInput,
  savingKey,
  testing,
  onKeyInputChange,
  onSave,
  onTest,
}: ApiKeyCardProps) {
  const [showKey, setShowKey] = useState(false);
  
  const keyType = config.id as ApiKeyType;
  const hasKey = apiKeysStatus[keyType];
  const keyPreview = apiKeysStatus[`${keyType}_preview` as keyof ApiKeysStatus] as string;
  const isSaving = savingKey === keyType;

  return (
    <Card className="bg-card border border-border">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-base">
          <Key className="h-4 w-4 text-primary" />
          {config.title}
        </CardTitle>
        <CardDescription>{config.description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>{config.id === "gemini" ? "Gemini API Key" : config.id === "aliyun" ? "DashScope API Key" : "API Key"}</Label>
            {hasKey && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3 text-green-500" />
                {keyPreview}
              </span>
            )}
          </div>
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Input
                type={showKey ? "text" : "password"}
                placeholder={hasKey ? "输入新密钥以更新..." : config.placeholder}
                value={keyInput}
                onChange={(e) => onKeyInputChange(e.target.value)}
                className="bg-card border-border pr-10"
              />
              {config.hasTestButton && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                  onClick={() => setShowKey(!showKey)}
                >
                  {showKey ? (
                    <EyeOff className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <Eye className="h-4 w-4 text-muted-foreground" />
                  )}
                </Button>
              )}
            </div>
            <Button 
              variant="outline" 
              onClick={onSave}
              disabled={isSaving || !keyInput.trim()}
            >
              {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            </Button>
            {config.hasTestButton && onTest && (
              <Button 
                variant="outline" 
                onClick={onTest}
                disabled={testing || (!keyInput.trim() && !hasKey)}
              >
                {testing ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
                <span className="ml-2">验证</span>
              </Button>
            )}
          </div>
          {config.helpText && config.helpLink && (
            <p className="text-xs text-muted-foreground">
              {config.helpText.replace("获取", "")}
              <a href={config.helpLink} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                {config.helpText.includes("Google") ? "Google AI Studio" : config.helpText.includes("阿里云") ? "阿里云 DashScope" : config.helpLink}
              </a>
              {" "}获取
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
