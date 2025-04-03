import { QueryClient, QueryFunction } from "@tanstack/react-query";

async function throwIfResNotOk(res: Response) {
  if (!res.ok) {
    const text = (await res.text()) || res.statusText;
    throw new Error(`${res.status}: ${text}`);
  }
}

// Get the base URL from environment or default to current host
const BASE_URL = import.meta.env.VITE_API_URL || `${window.location.protocol}//${window.location.host}`;

export async function apiRequest<T>(
  path: string,
  options: {
    method?: string;
    body?: unknown;
    headers?: Record<string, string>;
  } = {}
): Promise<T> {
  const url = new URL(path, BASE_URL).toString();
  const method = options.method || 'GET';

  const res = await fetch(url, {
    method,
    headers: {
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
    body: options.body ? JSON.stringify(options.body) : undefined,
    credentials: "include",
  });

  await throwIfResNotOk(res);
  return res.json();
}

type UnauthorizedBehavior = "returnNull" | "throw";

export const getQueryFn: <T>(options: {
  on401: UnauthorizedBehavior;
}) => QueryFunction<T> =
  ({ on401: unauthorizedBehavior }) =>
  async ({ queryKey }) => {
    const [path] = queryKey;
    if (typeof path !== 'string') {
      throw new Error('Query key must be a string');
    }

    const url = new URL(path, BASE_URL).toString();
    const isDirectDataEndpoint = path.startsWith('/data/');
    
    // Include special headers to ensure JSON response for direct data endpoints
    const res = await fetch(url, {
      credentials: "include",
      headers: isDirectDataEndpoint ? 
        {
          "Accept": "application/json", 
          "Content-Type": "application/json"
        } : {},
    });

    if (unauthorizedBehavior === "returnNull" && res.status === 401) {
      return null;
    }

    await throwIfResNotOk(res);
    return res.json();
  };

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      queryFn: getQueryFn({ on401: "throw" }),
      refetchInterval: false,
      refetchOnWindowFocus: true,  // Enable refetching when window gets focus
      staleTime: 60000,            // Consider data stale after 1 minute instead of Infinity
      retry: 1,                    // Allow 1 retry on failure
    },
    mutations: {
      retry: 1,                    // Allow 1 retry on mutation failure
    },
  },
});