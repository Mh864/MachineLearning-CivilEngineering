"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Droplets } from "lucide-react"

interface HeaderProps {
  apiStatus: boolean | null
}

const navItems = [
  { href: "/", label: "Dashboard" },
  { href: "/model-performance", label: "Model Performance" },
  { href: "/about", label: "About" },
]

export function Header({ apiStatus }: HeaderProps) {
  const pathname = usePathname()

  return (
    <header className="border-b border-border bg-card">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#185FA5]">
              <Droplets className="h-5 w-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-foreground">Flood Risk Predictor</h1>
              <p className="text-xs text-muted-foreground">
                Real-time river discharge analysis · 10 US gauge stations
              </p>
            </div>
          </div>

          <div className="flex items-center gap-6">
            <nav className="hidden md:flex items-center gap-1">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "px-3 py-2 text-sm font-medium rounded-md transition-colors",
                    pathname === item.href
                      ? "bg-[#185FA5] text-white"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </nav>

            <div className="flex items-center gap-2 text-sm">
              <div
                className={cn(
                  "h-2.5 w-2.5 rounded-full",
                  apiStatus === null
                    ? "bg-muted-foreground animate-pulse"
                    : apiStatus
                    ? "bg-emerald-500"
                    : "bg-red-500"
                )}
              />
              <span className="text-muted-foreground hidden sm:inline">
                {apiStatus === null
                  ? "Checking..."
                  : apiStatus
                  ? "API Connected"
                  : "API Offline"}
              </span>
            </div>
          </div>
        </div>

        {/* Mobile navigation */}
        <nav className="flex md:hidden items-center gap-1 pb-3 -mx-1 overflow-x-auto">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "px-3 py-1.5 text-sm font-medium rounded-md transition-colors whitespace-nowrap",
                pathname === item.href
                  ? "bg-[#185FA5] text-white"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  )
}
