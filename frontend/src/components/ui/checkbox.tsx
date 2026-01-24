import * as React from "react"
import { cn } from "@/lib/utils"
import { Check } from "lucide-react"

export interface CheckboxProps {
  checked?: boolean
  onCheckedChange?: (checked: boolean) => void
  disabled?: boolean
  className?: string
  onClick?: (e: React.MouseEvent) => void
}

const Checkbox = React.forwardRef<HTMLButtonElement, CheckboxProps>(
  ({ className, onCheckedChange, checked = false, disabled, onClick, ...props }, ref) => {
    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      e.stopPropagation();
      e.preventDefault();
      onClick?.(e);
      onCheckedChange?.(!checked);
    };

    return (
      <button
        type="button"
        role="checkbox"
        aria-checked={checked}
        ref={ref}
        disabled={disabled}
        onClick={handleClick}
        style={{
          backgroundColor: checked ? '#6366f1' : 'transparent',
          borderColor: '#6366f1',
        }}
        className={cn(
          "h-5 w-5 shrink-0 rounded border-2 ring-offset-background",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "flex items-center justify-center transition-all cursor-pointer hover:opacity-80",
          className
        )}
        {...props}
      >
        {checked && <Check className="h-3.5 w-3.5 text-white" strokeWidth={3} />}
      </button>
    )
  }
)
Checkbox.displayName = "Checkbox"

export { Checkbox }
