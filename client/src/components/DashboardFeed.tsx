import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { dashboardPosts } from "@shared/schema";

type DashboardPost = typeof dashboardPosts.$inferSelect;

export function DashboardFeed() {
  const [mounted, setMounted] = useState(false);

  // Only run queries after component has mounted
  useEffect(() => {
    setMounted(true);
  }, []);

  const { data: posts, isLoading, error } = useQuery<DashboardPost[]>({
    queryKey: ['/api/dashboard/posts'],
    // Refresh every 30 seconds
    refetchInterval: 30000,
    // Refresh when window regains focus
    refetchOnWindowFocus: true,
    // Only run query after component has mounted
    enabled: mounted,
  });

  if (!mounted || isLoading) {
    return (
      <Card className="w-full bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <CardHeader>
          <CardTitle>Agent Activity</CardTitle>
          <CardDescription>Loading latest updates...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="w-full bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <CardHeader>
          <CardTitle>Agent Activity</CardTitle>
          <CardDescription>Error loading updates</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
      <CardHeader>
        <CardTitle>Agent Activity</CardTitle>
        <CardDescription>Recent updates from ZerePy agents</CardDescription>
      </CardHeader>
      <CardContent>
        <ScrollArea className="h-[500px] pr-4">
          {posts?.map((post) => (
            <Card key={post.id} className="mb-4 bg-background/70 border border-primary/10">
              <CardHeader className="py-3">
                <CardTitle className="text-sm font-medium">{post.title || post.type}</CardTitle>
                <CardDescription>{new Date(post.createdAt).toLocaleString()}</CardDescription>
              </CardHeader>
              <CardContent className="py-2">
                <p className="text-sm">{post.content}</p>
                {post.type === 'tweet' && post.metadata && (
                  <div className="mt-2 text-sm text-muted-foreground flex items-center justify-between">
                    <span>Sentiment: {post.metadata.sentiment}</span>
                    <span className="px-2 py-0.5 rounded-full bg-primary/10 text-xs">
                      Confidence: {post.metadata.confidence}%
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </ScrollArea>
      </CardContent>
    </Card>
  );
}