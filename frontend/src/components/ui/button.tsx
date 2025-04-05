import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-neutral-950 disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-5 [&_svg]:shrink-0 dark:focus-visible:ring-neutral-300 uppercase tracking-wider",
  {
    variants: {
      variant: {
        default:
          "bg-transparent border-2 border-double border-[var(--primary)] text-[var(--primary)] hover:bg-[rgba(197,199,180,0.1)] hover:shadow-[0_0_10px_rgba(197,199,180,0.2)]",
        destructive:
          "bg-transparent border-2 border-double border-[#d84538] text-[#d84538] hover:bg-[rgba(216,69,56,0.1)] hover:shadow-[0_0_10px_rgba(216,69,56,0.2)]",
        outline:
          "bg-transparent border-2 border-double border-[var(--primary)] text-[var(--primary)] hover:bg-[rgba(197,199,180,0.1)] hover:shadow-[0_0_10px_rgba(197,199,180,0.2)]",
        secondary:
          "bg-[rgba(32,35,24,0.7)] border-2 border-double border-[var(--primary)] text-[var(--primary)] hover:bg-[rgba(197,199,180,0.1)] hover:shadow-[0_0_10px_rgba(197,199,180,0.2)]",
        ghost:
          "hover:bg-[rgba(197,199,180,0.1)] hover:text-[var(--primary)] hover:shadow-[0_0_10px_rgba(197,199,180,0.2)]",
        link: "text-[var(--primary)] underline-offset-4 hover:underline",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 px-3 text-xs",
        lg: "h-10 px-8",
        icon: "h-9 w-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  isLoading?: boolean;
  disabled?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant,
      size,
      asChild = false,
      isLoading,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {!(isLoading && size === "icon") && children}
      </Comp>
    );
  }
);
Button.displayName = "Button";

export { Button, buttonVariants };
