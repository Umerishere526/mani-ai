// ABOUTME: A "back" navigation link with a leading arrow icon, used atop detail pages.
// ABOUTME: Ported from mani-app's components/admin/BackLink.tsx, restyled to Tailwind.

import type { ReactNode } from "react";
import Link from "next/link";
import { ArrowLeftIcon } from "./icons";

interface BackLinkProps {
  href: string;
  children: ReactNode;
}

export function BackLink({ href, children }: BackLinkProps) {
  return (
    <Link
      href={href}
      className="mb-6 inline-flex items-center gap-1.5 text-sm text-mani-text-muted transition-colors duration-150 hover:text-mani-text"
    >
      <ArrowLeftIcon size={16} strokeWidth={1.75} />
      <span>{children}</span>
    </Link>
  );
}
