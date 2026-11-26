// ABOUTME: Email and password form for admin sign-in, posting to the signIn server action.
// ABOUTME: A client leaf only for the pending and error state useActionState gives it.

"use client";

import { useActionState } from "react";
import { signIn, type SignInState } from "@/lib/actions/auth";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.login;

const INPUT_CLASSES =
  "w-full rounded-mani-md border border-mani-border bg-mani-bg-card px-3.5 py-2.5 text-mani-text focus:border-mani-accent focus:ring-3 focus:ring-mani-accent-light focus:outline-none";

const INITIAL_STATE: SignInState = { error: null };

export function LoginForm() {
  const [state, formAction, isPending] = useActionState(signIn, INITIAL_STATE);

  return (
    <form action={formAction} className="space-y-4">
      <div>
        <label htmlFor="email" className="mb-1.5 block text-sm font-medium text-mani-text">
          {STRINGS.emailLabel}
        </label>
        <input
          id="email"
          name="email"
          type="email"
          autoComplete="email"
          required
          placeholder={STRINGS.emailPlaceholder}
          className={INPUT_CLASSES}
        />
      </div>

      <div>
        <label htmlFor="password" className="mb-1.5 block text-sm font-medium text-mani-text">
          {STRINGS.passwordLabel}
        </label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          className={INPUT_CLASSES}
        />
      </div>

      {state?.error && (
        <div role="alert" className="rounded-mani-md bg-mani-error-light p-3 text-sm text-mani-error">
          {state.error}
        </div>
      )}

      <button
        type="submit"
        disabled={isPending}
        className="w-full rounded-mani-md bg-mani-accent px-4 py-2 font-medium text-white transition-colors duration-200 hover:bg-mani-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isPending ? STRINGS.loading : STRINGS.signInButton}
      </button>
    </form>
  );
}
