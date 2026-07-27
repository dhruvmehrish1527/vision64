// Auth wrapper. When a Clerk publishable key is present, we mount ClerkProvider
// and wire its `getToken` into the API client. When VITE_AUTH_DEV_BYPASS is on
// (or no key is configured), we skip Clerk entirely so the app runs locally
// against the backend's matching dev bypass.

import { ClerkProvider, useAuth } from "@clerk/clerk-react";
import { useEffect, type ReactNode } from "react";
import { setTokenGetter } from "@/lib/api";

const CLERK_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY as string | undefined;
const DEV_BYPASS = import.meta.env.VITE_AUTH_DEV_BYPASS === "true";

function TokenBridge({ children }: { children: ReactNode }) {
  const { getToken } = useAuth();
  useEffect(() => {
    setTokenGetter(() => getToken());
  }, [getToken]);
  return <>{children}</>;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // Dev / unconfigured mode: no Clerk, backend uses its dev user.
  if (DEV_BYPASS || !CLERK_KEY) {
    return <>{children}</>;
  }
  return (
    <ClerkProvider publishableKey={CLERK_KEY} afterSignOutUrl="/">
      <TokenBridge>{children}</TokenBridge>
    </ClerkProvider>
  );
}

export const authEnabled = !DEV_BYPASS && !!CLERK_KEY;
