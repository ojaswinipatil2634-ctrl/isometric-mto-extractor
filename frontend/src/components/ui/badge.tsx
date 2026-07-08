import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-sm px-2 py-0.5 font-mono text-[11px] uppercase tracking-wider",
  {
    variants: {
      variant: {
        neutral: "bg-graphite-700/8 text-graphite-700 dark:bg-linework/10 dark:text-linework",
        warning: "bg-signal-amber/15 text-signal-amber",
        error: "bg-red-600/10 text-red-700 dark:text-red-400",
        success: "bg-emerald-600/10 text-emerald-700 dark:text-emerald-400",
        info: "bg-blueprint-500/10 text-blueprint-600 dark:text-linework-dim",
      },
    },
    defaultVariants: { variant: "neutral" },
  }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant, className }))} {...props} />;
}
