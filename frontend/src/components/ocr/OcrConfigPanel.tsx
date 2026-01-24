import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Settings2, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import type {
  OcrConfig,
  OcrStatus,
  LayoutModel,
  OcrEngine,
  DeepseekProvider,
  RouterMode,
} from "@/types/ocr";
import {
  LAYOUT_MODELS,
  GEMINI_MODELS,
  ALIYUN_MODELS,
  DEEPSEEK_PROVIDERS,
  ROUTER_MODES,
  needsDeepseekConfig,
  needsRouterConfig,
} from "@/lib/ocr-constants";

interface OcrConfigPanelProps {
  config: OcrConfig;
  ocrStatus: OcrStatus;
  progress: number;
  file: File | null;
  showAdvanced: boolean;
  onShowAdvancedChange: (show: boolean) => void;
  onLayoutModelChange: (v: LayoutModel) => void;
  onOcrEngineChange: (v: OcrEngine) => void;
  onOcrModelChange: (v: string) => void;
  onDeepseekProviderChange: (v: DeepseekProvider) => void;
  onDeepseekBaseUrlChange: (v: string) => void;
  onRouterModeChange: (v: RouterMode) => void;
  onOutsideRatioChange: (v: string) => void;
  onMinTextRatioChange: (v: string) => void;
  onGeminiProbeChange: (v: boolean) => void;
  onPageRangeChange: (v: string) => void;
  onDpiChange: (v: string) => void;
  onLayoutThreadsChange: (v: string) => void;
  onStartOcr: (layoutOnly: boolean) => void;
}

export function OcrConfigPanel({
  config,
  ocrStatus,
  progress,
  file,
  showAdvanced,
  onShowAdvancedChange,
  onLayoutModelChange,
  onOcrEngineChange,
  onOcrModelChange,
  onDeepseekProviderChange,
  onDeepseekBaseUrlChange,
  onRouterModeChange,
  onOutsideRatioChange,
  onMinTextRatioChange,
  onGeminiProbeChange,
  onPageRangeChange,
  onDpiChange,
  onLayoutThreadsChange,
  onStartOcr,
}: OcrConfigPanelProps) {
  const showDeepseekConfig = needsDeepseekConfig(config.layoutModel);
  const showRouterConfig = needsRouterConfig(config.layoutModel);
  const ocrModels = config.ocrEngine === "gemini" ? GEMINI_MODELS : ALIYUN_MODELS;

  return (
    <Card className="shadow-sm border-border/60">
      <CardHeader className="pb-3 pt-5 px-5">
        <div className="flex items-center gap-2">
          <Settings2 className="h-4 w-4 text-muted-foreground" />
          <CardTitle className="text-base">配置选项</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-5 px-5 pb-6">
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-muted-foreground">
              版面分析模型
            </Label>
            <Select
              value={config.layoutModel}
              onValueChange={(v) => onLayoutModelChange(v as LayoutModel)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {LAYOUT_MODELS.map((model) => (
                  <SelectItem key={model.value} value={model.value}>
                    {model.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-muted-foreground">
              OCR 引擎
            </Label>
            <Select
              value={config.ocrEngine}
              onValueChange={(v) => onOcrEngineChange(v as OcrEngine)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="gemini">Google Gemini</SelectItem>
                <SelectItem value="aliyun">阿里云 Qwen-VL</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-muted-foreground">
              OCR 模型
            </Label>
            <Select value={config.ocrModel} onValueChange={onOcrModelChange}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ocrModels.map((model) => (
                  <SelectItem key={model.value} value={model.value}>
                    {model.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs font-medium text-muted-foreground">
              处理页码
            </Label>
            <Input
              value={config.pageRange}
              onChange={(e) => onPageRangeChange(e.target.value)}
              placeholder="例如: 1-5 (留空则处理全部)"
              className="h-10 text-xs"
            />
          </div>

          {showDeepseekConfig && (
            <div className="space-y-1.5 animate-in slide-in-from-top-2">
              <Label className="text-xs font-medium text-muted-foreground">
                DeepSeek 配置
              </Label>
              <Select
                value={config.deepseekProvider}
                onValueChange={(v) =>
                  onDeepseekProviderChange(v as DeepseekProvider)
                }
              >
                <SelectTrigger className="h-10 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {DEEPSEEK_PROVIDERS.map((p) => (
                    <SelectItem key={p.value} value={p.value}>
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {config.deepseekProvider === "custom" && (
                <Input
                  value={config.deepseekBaseUrl}
                  onChange={(e) => onDeepseekBaseUrlChange(e.target.value)}
                  placeholder="Base URL"
                  className="h-8 text-xs mt-2"
                />
              )}
            </div>
          )}
        </div>

        <div className="border rounded-lg">
          <button
            onClick={() => onShowAdvancedChange(!showAdvanced)}
            className="w-full flex items-center justify-between p-3 text-xs font-medium hover:bg-muted/50 transition-colors"
          >
            <span>高级设置</span>
            {showAdvanced ? (
              <ChevronUp className="h-3.5 w-3.5" />
            ) : (
              <ChevronDown className="h-3.5 w-3.5" />
            )}
          </button>

          {showAdvanced && (
            <div className="p-3 border-t bg-muted/20 space-y-4 animate-in slide-in-from-top-2 duration-200">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label className="text-[10px] text-muted-foreground uppercase">
                    DPI
                  </Label>
                  <Input
                    value={config.dpi}
                    onChange={(e) => onDpiChange(e.target.value)}
                    className="h-8 text-xs"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label className="text-[10px] text-muted-foreground uppercase">
                    处理线程数
                  </Label>
                  <Input
                    value={config.layoutThreads}
                    onChange={(e) => onLayoutThreadsChange(e.target.value)}
                    className="h-8 text-xs"
                  />
                </div>
              </div>

              {showRouterConfig && (
                <div className="space-y-3 pt-2 border-t border-border/50">
                  <Label className="text-xs font-semibold">路由策略</Label>
                  <Select
                    value={config.routerMode}
                    onValueChange={(v) => onRouterModeChange(v as RouterMode)}
                  >
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ROUTER_MODES.map((mode) => (
                        <SelectItem key={mode.value} value={mode.value}>
                          {mode.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <div className="flex items-center justify-between">
                    <Label className="text-xs text-muted-foreground">
                      Gemini 探测
                    </Label>
                    <Switch
                      checked={config.geminiProbe}
                      onCheckedChange={onGeminiProbeChange}
                      className="scale-75 origin-right"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    <div className="space-y-1">
                      <Label className="text-[10px] text-muted-foreground uppercase">
                        Outside Ratio
                      </Label>
                      <Input
                        value={config.outsideRatio}
                        onChange={(e) => onOutsideRatioChange(e.target.value)}
                        className="h-7 text-[10px]"
                      />
                    </div>
                    <div className="space-y-1">
                      <Label className="text-[10px] text-muted-foreground uppercase">
                        Min Text Ratio
                      </Label>
                      <Input
                        value={config.minTextRatio}
                        onChange={(e) => onMinTextRatioChange(e.target.value)}
                        className="h-7 text-[10px]"
                      />
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="flex flex-col gap-2 pt-2">
          <Button
            onClick={() => onStartOcr(false)}
            disabled={!file || ocrStatus === "processing"}
            className="w-full font-semibold"
          >
            {ocrStatus === "processing" ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                处理中 {progress}%
              </>
            ) : (
              "开始识别"
            )}
          </Button>

          <Button
            variant="outline"
            onClick={() => onStartOcr(true)}
            disabled={!file || ocrStatus === "processing"}
            className="w-full text-xs h-8 text-muted-foreground"
          >
            仅分析版面
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
