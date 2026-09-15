// ABOUTME: Shown when a user lacks admin access. Visual only — nothing redirects here yet.
// ABOUTME: Ported from mani-app's app/admin/unauthorized/page.tsx.

import Link from "next/link";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.unauthorized;

export default function UnauthorizedPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-mani-bg">
      <div className="w-full max-w-md rounded-mani-lg bg-mani-bg-card p-8 text-center shadow-mani-card">
        <div className="mb-4 text-6xl" aria-hidden="true">
          🚫
        </div>
        <h1 className="mb-4 text-2xl font-bold text-mani-text">{STRINGS.title}</h1>
        <p className="mb-6 text-mani-text-muted">{STRINGS.body}</p>
        <Link
          href="/admin/login"
          className="inline-block rounded-mani-md bg-mani-accent px-4 py-2 font-medium text-white transition-colors duration-200 hover:bg-mani-accent-hover"
        >
          {STRINGS.backToLogin}
        </Link>
      </div>
    </div>
  );
}
