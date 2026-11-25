// ABOUTME: Inline form on a crisis event: the admin's note on what was done, and a Resolve button.
// ABOUTME: A client leaf only for the pending and error state of the resolveCrisisEvent action.

"use client";

import { useActionState } from "react";
import { resolveCrisisEvent } from "@/lib/actions/crisis-events";
import type { ActionResult } from "@/lib/actions/action-result";
import dictionary from "@/dictionaries/en.json";
import { FORM_INPUT_CLASSES } from "./form-field-classes";

const STRINGS = dictionary.admin.pages.crisisEvents;

const INITIAL_STATE: ActionResult = { error: null };

interface ResolveCrisisFormProps {
  eventId: string;
}

export function ResolveCrisisForm({ eventId }: ResolveCrisisFormProps) {
  const [state, formAction, isPending] = useActionState(resolveCrisisEvent.bind(null, eventId), INITIAL_STATE);

  return (
    <form action={formAction} className="flex min-w-64 flex-col gap-2">
      <label htmlFor={`resolution-${eventId}`} className="sr-only">
        {STRINGS.resolutionLabel}
      </label>
      <input
        id={`resolution-${eventId}`}
        name="resolution"
        type="text"
        required
        placeholder={STRINGS.resolutionPlaceholder}
        className={FORM_INPUT_CLASSES}
      />
      {state?.error && <p className="text-sm text-mani-error">{state.error}</p>}
      <button
        type="submit"
        disabled={isPending}
        className="self-end rounded-mani-md bg-mani-accent px-3 py-1.5 text-sm font-medium text-white transition-colors duration-200 hover:bg-mani-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isPending ? STRINGS.resolving : STRINGS.resolveButton}
      </button>
    </form>
  );
}
