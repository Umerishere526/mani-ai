// ABOUTME: Merges NativeWind class names, resolving conflicts so the last class wins.
// ABOUTME: Wraps clsx for conditional classes and tailwind-merge for deduplication.

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
