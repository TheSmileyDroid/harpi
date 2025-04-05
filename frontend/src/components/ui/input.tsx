import * as React from "react";

import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-9 w-full rounded-none border-2 border-double border-[var(--primary)] bg-[rgba(12,12,14,0.7)] px-3 py-1 text-[var(--primary)] text-base tracking-wide shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-[var(--secondary)] placeholder:opacity-70 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--primary)] focus-visible:shadow-[0_0_10px_rgba(197,199,180,0.2)] disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input };
