// ABOUTME: Login page — password and magic-link tabs. Visual only, no auth backend yet.
// ABOUTME: Ported from mani-app's app/admin/login/page.tsx.

"use client";

import { useState, type SubmitEvent } from "react";
import { cn } from "@/lib/utils";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.login;

export default function AdminLoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const error: string | null = null;
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"login" | "magic">("login");
  const [magicLinkSent, setMagicLinkSent] = useState(false);

  const handleLogin = (e: SubmitEvent) => {
    e.preventDefault();
    setLoading(true);

    // No auth backend yet — visual only.
    console.log("admin login submit", { mode, email });
    window.setTimeout(() => {
      setLoading(false);
      if (mode === "magic") setMagicLinkSent(true);
    }, 400);
  };

  if (magicLinkSent) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-mani-bg">
        <div className="w-full max-w-md rounded-mani-lg bg-mani-bg-card p-8 text-center shadow-mani-card">
          <h1 className="mb-4 text-2xl font-bold text-mani-text">{STRINGS.checkEmailTitle}</h1>
          <p className="mb-4 text-mani-text-muted">
            {STRINGS.checkEmailBody.replace("{email}", email)}
          </p>
          <p className="text-sm text-mani-text-light">{STRINGS.checkEmailHelper}</p>
          <button
            type="button"
            onClick={() => setMagicLinkSent(false)}
            className="mt-6 text-sm text-mani-accent hover:text-mani-accent-hover"
          >
            {STRINGS.useDifferentEmail}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-mani-bg">
      <div className="w-full max-w-md rounded-mani-lg bg-mani-bg-card p-8 shadow-mani-card">
        <h1 className="mb-6 text-center text-2xl font-bold text-mani-text">{STRINGS.title}</h1>

        <div className="mb-6 flex border-b border-mani-border">
          <button
            type="button"
            onClick={() => setMode("login")}
            className={cn(
              "flex-1 pb-2 text-sm font-medium",
              mode === "login" ? "border-b-2 border-mani-accent text-mani-accent" : "text-mani-text-muted",
            )}
          >
            {STRINGS.passwordTab}
          </button>
          <button
            type="button"
            onClick={() => setMode("magic")}
            className={cn(
              "flex-1 pb-2 text-sm font-medium",
              mode === "magic" ? "border-b-2 border-mani-accent text-mani-accent" : "text-mani-text-muted",
            )}
          >
            {STRINGS.magicLinkTab}
          </button>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-mani-text">
              {STRINGS.emailLabel}
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder={STRINGS.emailPlaceholder}
              className="w-full rounded-mani-md border border-mani-border bg-mani-bg-card px-3.5 py-2.5 text-mani-text focus:border-mani-accent focus:ring-3 focus:ring-mani-accent-light focus:outline-none"
            />
          </div>

          {mode === "login" && (
            <div>
              <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-mani-text">
                {STRINGS.passwordLabel}
              </label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full rounded-mani-md border border-mani-border bg-mani-bg-card px-3.5 py-2.5 text-mani-text focus:border-mani-accent focus:ring-3 focus:ring-mani-accent-light focus:outline-none"
              />
            </div>
          )}

          {error && <div className="rounded-mani-md bg-mani-error-light p-3 text-sm text-mani-error">{error}</div>}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-mani-md bg-mani-accent px-4 py-2 font-medium text-white transition-colors duration-200 hover:bg-mani-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? STRINGS.loading : mode === "magic" ? STRINGS.sendMagicLinkButton : STRINGS.signInButton}
          </button>
        </form>
      </div>
    </div>
  );
}
