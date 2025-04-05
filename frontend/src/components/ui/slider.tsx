import * as SliderPrimitive from "@radix-ui/react-slider";
import * as React from "react";

import { cn } from "@/lib/utils";

const Slider = React.forwardRef<
  React.ElementRef<typeof SliderPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof SliderPrimitive.Root>
>(({ className, ...props }, ref) => (
  <SliderPrimitive.Root
    ref={ref}
    className={cn(
      "relative flex w-full touch-none select-none items-center",
      className
    )}
    {...props}
  >
    <SliderPrimitive.Track className="relative h-1.5 w-full grow overflow-hidden bg-[rgba(32,35,24,0.8)] before:content-[''] before:absolute before:top-0 before:left-0 before:right-0 before:bottom-0 before:border before:border-double before:border-[var(--primary)] before:opacity-30">
      <SliderPrimitive.Range className="absolute h-full bg-[var(--primary)]" />
    </SliderPrimitive.Track>
    <SliderPrimitive.Thumb className="block h-5 w-5 border-2 border-double border-[var(--primary)] bg-[var(--background)] ring-offset-white transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[var(--primary)] focus-visible:ring-offset-1 disabled:pointer-events-none disabled:opacity-50" />
  </SliderPrimitive.Root>
));
Slider.displayName = SliderPrimitive.Root.displayName;

export { Slider };
