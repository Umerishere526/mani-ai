// ABOUTME: Shared Tailwind class strings for admin form fields (input/textarea/select/label).
// ABOUTME: Replaces source's global `input[type=...]`/`label`/`.helper-text` CSS selectors.

export const FORM_INPUT_CLASSES =
  "w-full rounded-mani-md border border-mani-border bg-mani-bg-card px-3.5 py-2.5 text-[0.9375rem] text-mani-text transition-colors duration-150 placeholder:text-mani-text-light focus:border-mani-accent focus:outline-none focus:ring-3 focus:ring-mani-accent-light disabled:cursor-not-allowed disabled:bg-mani-bg disabled:opacity-70";

export const FORM_FILE_INPUT_CLASSES = `${FORM_INPUT_CLASSES} file:mr-3 file:cursor-pointer file:rounded-mani-sm file:border-0 file:bg-mani-accent-light file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-mani-accent`;

export const FORM_CHECKBOX_CLASSES = "h-4 w-4 accent-mani-accent";

export const FORM_TEXTAREA_CLASSES = `${FORM_INPUT_CLASSES} font-mono leading-relaxed`;

export const FORM_LABEL_CLASSES = "mb-1.5 block text-[0.9375rem] font-medium text-mani-text";

export const FORM_HELPER_CLASSES = "mt-1.5 text-[0.8125rem] text-mani-text-light";

export const FORM_ERROR_CLASSES = "mt-1 text-sm text-mani-error";
