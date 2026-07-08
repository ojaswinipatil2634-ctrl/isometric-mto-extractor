"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/theme/ThemeToggle";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Upload" },
  { href: "/history", label: "History" },
];

export function Header() {
  const pathname = usePathname();

  return (
    <header className="border-b border-graphite-700/15 bg-vellum-50/90 backdrop-blur dark:border-linework/15 dark:bg-print-900/90">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-6">
        <Link href="/" className="flex items-baseline gap-2">
          <span className="font-display text-lg text-graphite-900 dark:text-linework">MTO Extractor</span>
        </Link>

        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map((item) => {
            const active = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "rounded-sm px-3 py-1.5 text-sm font-medium transition-colors",
                  active
                    ? "bg-blueprint-600 text-vellum-50 dark:bg-linework dark:text-print-900"
                    : "text-graphite-700 hover:bg-graphite-700/5 dark:text-linework dark:hover:bg-linework/10"
                )}
              >
                {item.label}
              </Link>
            );
          })}
          <div className="ml-2">
            <ThemeToggle />
          </div>
        </nav>
      </div>
    </header>
  );
}
