// ABOUTME: Admin sign-in page: a server-rendered card around the password form.
// ABOUTME: The form is the only client leaf; sign-in itself runs in a server action.

import { LoginForm } from "@/components/auth/login-form";
import dictionary from "@/dictionaries/en.json";

const STRINGS = dictionary.admin.pages.login;

export default function AdminLoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-mani-bg">
      <div className="w-full max-w-md rounded-mani-lg bg-mani-bg-card p-8 shadow-mani-card">
        <h1 className="mb-6 text-center text-2xl font-bold text-mani-text">{STRINGS.title}</h1>
        <LoginForm />
      </div>
    </main>
  );
}
