import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Cpu } from "lucide-react";
import type { LLMConfig } from "@/types/settings";
import { LLM_PROVIDERS } from "@/lib/settings-constants";

interface LLMConfigCardProps {
  config: LLMConfig;
  onProviderChange: (provider: string) => void;
  onModelChange: (model: string) => void;
  onBaseUrlChange: (baseUrl: string) => void;
}

export function LLMConfigCard({
  config,
  onProviderChange,
  onModelChange,
  onBaseUrlChange,
}: LLMConfigCardProps) {
  const handleProviderChange = (v: string) => {
    onProviderChange(v);
    const provider = LLM_PROVIDERS.find(p => p.value === v);
    if (provider?.baseUrl) {
      onBaseUrlChange(provider.baseUrl);
      onModelChange(provider.model || "");
    }
  };

  return (
    <Card className="bg-card border border-border">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-primary" />
          LLM 模型配置
        </CardTitle>
        <CardDescription>
          配置用于生成题目答案的大语言模型。支持 DeepSeek 官方、硅基流动或任意 OpenAI 兼容 API。
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>服务商</Label>
            <Select value={config.provider} onValueChange={handleProviderChange}>
              <SelectTrigger className="bg-card border-border">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-card border-border">
                {LLM_PROVIDERS.map(provider => (
                  <SelectItem key={provider.value} value={provider.value}>
                    {provider.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="model">模型名称</Label>
            <Input
              id="model"
              placeholder="deepseek-chat"
              value={config.model}
              onChange={(e) => onModelChange(e.target.value)}
              className="bg-card border-border"
            />
          </div>
        </div>

        {config.provider === "custom" && (
          <div className="space-y-2 animate-fade-in">
            <Label htmlFor="base-url">API 地址</Label>
            <Input
              id="base-url"
              placeholder="https://api.example.com/v1"
              value={config.base_url}
              onChange={(e) => onBaseUrlChange(e.target.value)}
              className="bg-card border-border"
            />
          </div>
        )}

        <div className="pt-4 border-t border-border/50">
          <div className="flex items-start gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Cpu className="h-5 w-5 text-primary" />
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">模型说明</p>
              <p className="text-xs text-muted-foreground">
                修改模型配置后，请点击右上角"保存更改"按钮。API 密钥请在"API密钥"标签页中配置。
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
