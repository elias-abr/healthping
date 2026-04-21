"use client";

import { useRouter } from "next/navigation";

import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";

export function UserMenu() {
  const { user, isLoading, logout } = useAuth();
  const router = useRouter();

  if (isLoading) return null;

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={() => router.push("/login")}>
          Log in
        </Button>
        <Button size="sm" onClick={() => router.push("/signup")}>
          Sign up
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-muted-foreground text-sm hidden sm:block">{user.email}</span>
      <Button
        variant="outline"
        size="sm"
        onClick={async () => {
          await logout();
          router.push("/");
        }}
      >
        Log out
      </Button>
    </div>
  );
}
