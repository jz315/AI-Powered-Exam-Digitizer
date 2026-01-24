export interface LLMConfig {
  provider: string;
  model: string;
  base_url: string;
}

export interface ApiKeysStatus {
  llm: boolean;
  llm_preview: string;
  gemini: boolean;
  gemini_preview: string;
  aliyun: boolean;
  aliyun_preview: string;
  deepseek_modelverse: boolean;
  deepseek_modelverse_preview: string;
  deepseek_siliconflow: boolean;
  deepseek_siliconflow_preview: string;
  deepseek_custom: boolean;
  deepseek_custom_preview: string;
}

export interface WebSettings {
  llm: LLMConfig;
  theme: string;
  auto_save: boolean;
  has_api_key: boolean;
  api_key_preview: string;
  api_keys: ApiKeysStatus;
}

export interface ApiKeyConfig {
  id: string;
  title: string;
  description: string;
  placeholder: string;
  helpText?: string;
  helpLink?: string;
  hasTestButton?: boolean;
}

export type ApiKeyType = 'llm' | 'gemini' | 'aliyun' | 'deepseek_modelverse' | 'deepseek_siliconflow' | 'deepseek_custom';
