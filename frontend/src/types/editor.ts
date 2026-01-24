export interface ValidationIssue {
  line: number;
  message: string;
  severity: "error" | "warning";
}

export type ValidationStatus = "valid" | "invalid" | "unknown";
