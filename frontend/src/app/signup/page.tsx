import Link from "next/link";

import { SignupForm } from "@/components/SignupForm";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function SignupPage() {
  return (
    <main className="bg-background flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Create an account</CardTitle>
          <CardDescription>Sign up to manage your endpoint monitoring.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <SignupForm />
          <p className="text-muted-foreground text-center text-sm">
            Already have an account?{" "}
            <Link href="/login" className="text-foreground underline underline-offset-4">
              Sign in
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  );
}
