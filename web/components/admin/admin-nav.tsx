// ABOUTME: Sidebar navigation for the admin dashboard — brand, nav links, user/sign-out footer.
// ABOUTME: Ported from mani-app's components/admin/AdminNav.tsx, restyled to Tailwind.

"use client";

import type { ReactNode } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Server, BookOpen, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import dictionary from "@/dictionaries/en.json";
import { FileTextIcon, LogOutIcon } from "@/components/shared";

const NAV_STRINGS = dictionary.admin.nav;

interface NavItem {
  label: string;
  href: string;
  icon: ReactNode;
  requiresEditing?: boolean;
}

const NAV_ITEMS: NavItem[] = [
  {
    label: NAV_STRINGS.prompts,
    href: "/admin/prompts",
    icon: <FileTextIcon size={18} strokeWidth={1.75} />,
    requiresEditing: true,
  },
  {
    label: NAV_STRINGS.providers,
    href: "/admin/providers",
    icon: <Server size={18} strokeWidth={1.75} />,
    requiresEditing: true,
  },
  {
    label: NAV_STRINGS.exercises,
    href: "/admin/exercises",
    icon: <BookOpen size={18} strokeWidth={1.75} />,
  },
  {
    label: NAV_STRINGS.chats,
    href: "/admin/chats",
    icon: <MessageSquare size={18} strokeWidth={1.75} />,
  },
];

interface AdminNavProps {
  user: {
    email: string;
  };
  editingEnabled?: boolean;
}

export function AdminNav({ user, editingEnabled = false }: AdminNavProps) {
  const pathname = usePathname();
  const router = useRouter();

  const handleSignOut = () => {
    router.push("/auth/login");
    router.refresh();
  };

  return (
    <nav className="flex min-h-screen w-64 flex-col bg-mani-sidebar bg-[url('/textures/noise.svg')] bg-blend-soft-light">
      <div className="border-b border-white/8 px-5 py-6">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-mani-accent">
            <span className="text-sm font-semibold text-white">M</span>
          </div>
          <h1 className="text-base font-semibold tracking-tight text-white">
            {NAV_STRINGS.brand}
          </h1>
        </div>
      </div>

      <div className="flex-1 px-3 py-4">
        <div className="space-y-1">
          {NAV_ITEMS.filter((item) => !item.requiresEditing || editingEnabled).map((item) => {
            const isActive = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  "-ml-0.75 flex items-center gap-3 rounded-lg border-l-[3px] px-3 py-2.5 transition-all duration-200",
                  isActive
                    ? "border-mani-accent bg-mani-accent/20 text-white"
                    : "border-transparent text-white/65 hover:bg-white/5 hover:text-white",
                )}
              >
                <span
                  className={cn(
                    isActive ? "text-mani-accent-hover opacity-100" : "opacity-80",
                  )}
                >
                  {item.icon}
                </span>
                <span className="text-sm font-medium">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </div>

      <div className="border-t border-white/8 px-4 py-4">
        <div className="mb-3 truncate text-sm text-white/50">{user.email}</div>
        <div className="flex items-center justify-between">
          <span className="rounded-full bg-mani-accent-light px-2.5 py-1 text-xs font-medium text-mani-accent">
            {NAV_STRINGS.adminBadge}
          </span>
          <button
            type="button"
            onClick={handleSignOut}
            className="flex items-center gap-1.5 text-sm text-white/50 transition-colors duration-200 hover:text-white"
          >
            <LogOutIcon size={16} strokeWidth={1.75} />
            <span>{NAV_STRINGS.signOut}</span>
          </button>
        </div>
      </div>
    </nav>
  );
}
