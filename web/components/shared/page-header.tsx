// ABOUTME: The title row at the top of an admin list page, with an optional primary action link.
// ABOUTME: Holds the page's single H1.

import Link from "next/link";

interface PageHeaderProps {
  title: string;
  action?: { label: string; href: string };
}

export function PageHeader({ title, action }: PageHeaderProps) {
  return (
    <div className="mb-8 flex items-center justify-between gap-4">
      <h1 className="text-[1.75rem] font-semibold tracking-tight text-mani-text">{title}</h1>
      {action && (
        <Link
          href={action.href}
          className="inline-flex shrink-0 items-center justify-center gap-2 rounded-mani-md bg-mani-accent px-5 py-2.5 text-[0.9375rem] font-medium text-white shadow-mani-sm transition-colors duration-200 hover:bg-mani-accent-hover"
        >
          {action.label}
        </Link>
      )}
    </div>
  );
}
