import type { Clerk } from '@clerk/clerk-js'

const publishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY || ''

/**
 * Clerk is optional. Without a publishable key the app runs anonymously and the
 * auth UI falls back to a neutral link instead of crashing.
 */
export const clerkEnabled = Boolean(publishableKey)

let instance: Clerk | null = null
let loading: Promise<Clerk | null> | null = null

export async function initClerk(): Promise<Clerk | null> {
  if (!clerkEnabled) return null
  if (instance) return instance
  if (!loading) {
    loading = (async () => {
      try {
        // Dynamic import keeps clerk-js out of the bundle when it is disabled.
        const { Clerk: ClerkCtor } = await import('@clerk/clerk-js')
        const clerk = new ClerkCtor(publishableKey)
        await clerk.load()
        instance = clerk
        return clerk
      } catch (e) {
        console.warn('[clerk] initialization failed; continuing anonymously', e)
        return null
      }
    })()
  }
  return loading
}

export function getClerk(): Clerk | null {
  return instance
}

export async function getSessionToken(): Promise<string | null> {
  const clerk = getClerk()
  if (!clerk?.session) return null
  try {
    return await clerk.session.getToken()
  } catch {
    return null
  }
}
