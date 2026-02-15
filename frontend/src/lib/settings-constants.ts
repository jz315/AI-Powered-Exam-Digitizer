import type { LLMConfig, WebSettings, ApiKeyConfig } from "@/types/settings";
import { API_BASE } from "./constants";

export { API_BASE };

export const DEFAULT_LLM_CONFIG: LLMConfig = {
  provider: "deepseek",
  model: "deepseek-chat",
  base_url: "https://api.deepseek.com/v1",
};

export const DEFAULT_SETTINGS: WebSettings = {
  llm: DEFAULT_LLM_CONFIG,
  theme: "dark",
  auto_save: true,
  has_api_key: false,
  api_key_preview: "",
  api_keys: {
    llm: false,
    llm_preview: "",
    gemini: false,
    gemini_preview: "",
    aliyun: false,
    aliyun_preview: "",
    deepseek_modelverse: false,
    deepseek_modelverse_preview: "",
    deepseek_siliconflow: false,
    deepseek_siliconflow_preview: "",
    deepseek_custom: false,
    deepseek_custom_preview: "",
  },
};

export const API_KEY_CONFIGS: ApiKeyConfig[] = [
  {
    id: "llm",
    title: "DeepSeek 官方",
    description: "api.deepseek.com - 用于 LLM 生成答案",
    placeholder: "sk-...",
    hasTestButton: true,
  },
  {
    id: "deepseek_siliconflow",
    title: "硅基流动 (SiliconFlow)",
    description: "api.siliconflow.cn - 用于 LLM 和 DeepSeek OCR",
    placeholder: "sk-...",
  },
  {
    id: "deepseek_modelverse",
    title: "ModelVerse",
    description: "api.modelverse.cn - 用于 DeepSeek OCR",
    placeholder: "sk-...",
  },
  {
    id: "gemini",
    title: "Google",
    description: "generativelanguage.googleapis.com - 用于 Gemini OCR",
    placeholder: "AIza...",
    helpText: "可在 Google AI Studio 获取",
    helpLink: "https://aistudio.google.com/apikey",
  },
  {
    id: "aliyun",
    title: "阿里云",
    description: "dashscope.aliyuncs.com - 用于 Qwen-VL OCR",
    placeholder: "sk-...",
    helpText: "可在 阿里云 DashScope 获取",
    helpLink: "https://dashscope.console.aliyun.com/",
  },
  {
    id: "deepseek_custom",
    title: "自定义端点",
    description: "自定义 OpenAI 兼容 API - 用于 LLM 或 DeepSeek OCR",
    placeholder: "sk-...",
  },
];

export const LLM_PROVIDERS = [
  { value: "deepseek", label: "DeepSeek 官方", baseUrl: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  { value: "siliconflow", label: "硅基流动", baseUrl: "https://api.siliconflow.cn/v1", model: "deepseek-ai/DeepSeek-V3" },
  { value: "custom", label: "自定义 OpenAI 兼容" },
];

export const THEME_OPTIONS = [
  { value: "light", label: "浅色" },
  { value: "dark", label: "深色" },
  { value: "system", label: "跟随系统" },
];
