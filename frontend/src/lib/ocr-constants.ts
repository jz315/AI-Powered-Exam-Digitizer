import type { LayoutModelOption, OcrConfig } from "@/types/ocr";

export const LAYOUT_MODELS: LayoutModelOption[] = [
  { value: "auto_router", label: "Auto Router (Hybrid)" },
  { value: "doclayout_yolo", label: "DocLayout-YOLO (Local)" },
  { value: "deepseek_ocr", label: "DeepSeek OCR (Cloud)" },
  { value: "pp_doclayout", label: "PP-DocLayout (Paddle)" },
];

export const GEMINI_MODELS = [
  { value: "gemini-2.0-flash", label: "Gemini 2.0 Flash" },
  { value: "gemini-2.0-pro-exp", label: "Gemini 2.0 Pro Exp" },
  { value: "gemini-1.5-pro", label: "Gemini 1.5 Pro" },
  { value: "gemini-1.5-flash", label: "Gemini 1.5 Flash" },
];

export const ALIYUN_MODELS = [
  { value: "qwen-vl-max", label: "Qwen-VL Max" },
  { value: "qwen-vl-plus", label: "Qwen-VL Plus" },
];

export const DEEPSEEK_PROVIDERS = [
  { value: "modelverse", label: "ModelVerse (官方)" },
  { value: "siliconflow", label: "SiliconFlow (硅基流动)" },
  { value: "custom", label: "自定义端点" },
];

export const ROUTER_MODES = [
  { value: "any", label: "Any (任意)" },
  { value: "textness", label: "Textness (文本优先)" },
  { value: "second_pass", label: "Second Pass (二次确认)" },
];

export const DEFAULT_OCR_CONFIG: OcrConfig = {
  layoutModel: "auto_router",
  ocrEngine: "gemini",
  ocrModel: "gemini-2.0-flash",
  deepseekProvider: "modelverse",
  deepseekBaseUrl: "",
  routerMode: "second_pass",
  outsideRatio: "0.01",
  minTextRatio: "0.0005",
  geminiProbe: false,
  geminiProbeModel: "gemini-2.5-flash-lite",
  pageRange: "",
  dpi: "200",
  layoutThreads: "1",
};

export const needsDeepseekConfig = (layoutModel: string): boolean => {
  return layoutModel === "deepseek_ocr" || layoutModel === "auto_router";
};

export const needsRouterConfig = (layoutModel: string): boolean => {
  return layoutModel === "auto_router";
};
