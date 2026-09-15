// ABOUTME: Search form for the Chats list — filters threads by user email or ID.
// ABOUTME: Ported from mani-app's app/admin/chats/ChatSearchForm.tsx, restyled to Tailwind.

"use client";

import { useRouter } from "next/navigation";
import { useState, useTransition, type SubmitEvent } from "react";
import { Search } from "lucide-react";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.chats;

interface ChatSearchFormProps {
  initialSearch?: string;
}

export function ChatSearchForm({ initialSearch = "" }: ChatSearchFormProps) {
  const router = useRouter();
  const [search, setSearch] = useState(initialSearch);
  const [isPending, startTransition] = useTransition();

  const handleSubmit = (e: SubmitEvent) => {
    e.preventDefault();
    startTransition(() => {
      const params = new URLSearchParams();
      if (search.trim()) {
        params.set("search", search.trim());
      }
      router.push(`/admin/chats?${params.toString()}`);
    });
  };

  const handleClear = () => {
    setSearch("");
    startTransition(() => {
      router.push("/admin/chats");
    });
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-3">
      <div className="relative max-w-md flex-1">
        <Search size={18} className="absolute top-1/2 left-3 -translate-y-1/2 text-mani-text-light" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={STRINGS.searchPlaceholder}
          className="w-full rounded-mani-md border border-mani-border bg-mani-bg-card py-2.5 pr-3.5 pl-10 text-[0.9375rem] text-mani-text focus:border-mani-accent focus:ring-3 focus:ring-mani-accent-light focus:outline-none"
        />
      </div>
      <button
        type="submit"
        disabled={isPending}
        className="inline-flex items-center justify-center gap-2 rounded-mani-md bg-mani-accent px-5 py-2.5 text-[0.9375rem] font-medium text-white shadow-mani-sm transition-colors duration-200 hover:bg-mani-accent-hover disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isPending ? STRINGS.searching : STRINGS.searchButton}
      </button>
      {initialSearch && (
        <button
          type="button"
          onClick={handleClear}
          disabled={isPending}
          className="inline-flex items-center justify-center gap-2 rounded-mani-md border border-mani-border px-5 py-2.5 text-[0.9375rem] font-medium text-mani-text transition-colors duration-200 hover:border-mani-text-light hover:bg-mani-bg disabled:cursor-not-allowed disabled:opacity-50"
        >
          {STRINGS.clearButton}
        </button>
      )}
    </form>
  );
}
