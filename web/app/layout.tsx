// ABOUTME: Root layout for every page: fonts, global styles, and the metadata shared by the whole admin.
// ABOUTME: Pages are never indexed; the admin lives behind sign-in.

import type { Metadata } from "next";
import { Montserrat, JetBrains_Mono } from "next/font/google";
import dictionary from "@/dictionaries/en.json";
import "./globals.css";

const montserrat = Montserrat({
  variable: "--font-montserrat",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500"],
});

// A private admin tool: no page of it belongs in a search index.
export const metadata: Metadata = {
  title: dictionary.admin.meta.title,
  description: dictionary.admin.meta.description,
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${montserrat.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
