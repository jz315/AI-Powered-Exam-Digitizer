
import { cn } from "@/lib/utils"

type ButtonVariant = "default" | "outline" | "ghost" | "destructive" | "secondary" | "link"
type ButtonSize = "sm" | "md" | "lg" | "icon"

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant
  size?: ButtonSize
}

export function Button({
  className,
  variant = "default",
  size = "md",
  type = "button",
  ...props
}: ButtonProps) {
  const variants: Record<ButtonVariant, string> = {
    default: "bg-slate-900 text-white shadow hover:bg-slate-900/90",
    outline:
      "border border-slate-200 bg-white text-slate-900 shadow-sm hover:bg-slate-50",
    ghost: "bg-transparent text-slate-700 hover:bg-slate-100",
    destructive: "bg-red-600 text-white shadow hover:bg-red-600/90",
    secondary: "bg-slate-100 text-slate-900 hover:bg-slate-100/80",
    link: "text-slate-900 underline-offset-4 hover:underline",
  }

  const sizes: Record<ButtonSize, string> = {
    sm: "h-8 px-3 text-xs",
    md: "h-9 px-4 text-sm",
    lg: "h-10 px-8 text-base",
    icon: "h-9 w-9 p-0",
  }

  return (
    <button
      type={type}
      className={cn(
        "inline-flex items-center justify-center rounded-md font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-300 focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    />
  )
}
