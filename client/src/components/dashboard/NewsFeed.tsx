import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Newspaper, AlertCircle, ExternalLink } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import CryptoPanicWidget from "../CryptoPanicWidget";

interface NewsArticle {
  title: string;
  source: string;
  time: string;
  url?: string;
  category?: string;
}

interface NewsFeedProps {
  newsData?: {
    articles: NewsArticle[];
  };
  isLoading?: boolean;
}

export function NewsFeed({ newsData, isLoading }: NewsFeedProps) {
  if (isLoading) {
    return (
      <Card className="bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Newspaper className="h-5 w-5 text-primary" />
            Market News
          </CardTitle>
          <CardDescription>Latest cryptocurrency market news and updates</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <Card key={i} className="p-4 bg-background/70 border border-primary/10">
                <div className="animate-pulse h-5 w-4/5 bg-muted rounded mb-2"></div>
                <div className="flex justify-between">
                  <div className="animate-pulse h-4 w-24 bg-muted rounded"></div>
                  <div className="animate-pulse h-4 w-16 bg-muted rounded"></div>
                </div>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const articles = newsData?.articles || [];

  if (articles.length === 0) {
    return (
      <Card className="bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Newspaper className="h-5 w-5 text-primary" />
            Market News
          </CardTitle>
          <CardDescription>Latest cryptocurrency market news and updates</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <AlertCircle className="h-12 w-12 mx-auto mb-2 opacity-20" />
            <p>No news articles available</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Sample categories for articles that don't have one
  const categories = ["DeFi", "NFT", "Layer2", "Market", "Technical"];

  return (
    <Card className="bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Newspaper className="h-5 w-5 text-primary" />
          Market News
        </CardTitle>
        <CardDescription>Latest cryptocurrency market news and updates</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="internal" className="w-full">
          <TabsList className="w-full mb-4">
            <TabsTrigger value="internal" className="w-1/2">Internal Feed</TabsTrigger>
            <TabsTrigger value="cryptopanic" className="w-1/2">CryptoPanic</TabsTrigger>
          </TabsList>
          
          <TabsContent value="internal" className="mt-0">
            <ScrollArea className="h-[400px] pr-4">
              <div className="space-y-4">
                {articles.map((article, index) => (
                  <Card 
                    key={index} 
                    className="p-4 bg-background/70 border border-primary/10 hover:bg-background/80 transition-colors"
                  >
                    <div className="mb-2 flex justify-between items-start">
                      <h3 className="font-medium">{article.title}</h3>
                      <Badge variant="outline" className="ml-2 shrink-0">
                        {article.category || categories[index % categories.length]}
                      </Badge>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                      <p className="text-muted-foreground">{article.source}</p>
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">
                          {typeof article.time === 'string' ? new Date(article.time).toLocaleString() : article.time}
                        </span>
                        {article.url && (
                          <a 
                            href={article.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:text-primary/80"
                          >
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        )}
                      </div>
                    </div>
                  </Card>
                ))}
                
                {/* Add mock news to demonstrate pagination/scrolling */}
                {articles.length < 5 && (
                  <>
                    <Card className="p-4 bg-background/70 border border-primary/10 hover:bg-background/80 transition-colors">
                      <div className="mb-2 flex justify-between items-start">
                        <h3 className="font-medium">Sonic Chain Announces New DeFi Partnerships</h3>
                        <Badge variant="outline" className="ml-2 shrink-0">
                          Ecosystem
                        </Badge>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <p className="text-muted-foreground">SonicNews</p>
                        <span className="text-xs text-muted-foreground">{new Date().toLocaleString()}</span>
                      </div>
                    </Card>
                    
                    <Card className="p-4 bg-background/70 border border-primary/10 hover:bg-background/80 transition-colors">
                      <div className="mb-2 flex justify-between items-start">
                        <h3 className="font-medium">Market Analysis: Weekly TVL and Volume Trends</h3>
                        <Badge variant="outline" className="ml-2 shrink-0">
                          Analysis
                        </Badge>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <p className="text-muted-foreground">ChainAnalytics</p>
                        <span className="text-xs text-muted-foreground">{new Date().toLocaleString()}</span>
                      </div>
                    </Card>
                    
                    <Card className="p-4 bg-background/70 border border-primary/10 hover:bg-background/80 transition-colors">
                      <div className="mb-2 flex justify-between items-start">
                        <h3 className="font-medium">New Cross-Chain Bridge Connects Sonic to Major L1s</h3>
                        <Badge variant="outline" className="ml-2 shrink-0">
                          Bridge
                        </Badge>
                      </div>
                      <div className="flex justify-between items-center text-sm">
                        <p className="text-muted-foreground">ZerePy News</p>
                        <span className="text-xs text-muted-foreground">{new Date().toLocaleString()}</span>
                      </div>
                    </Card>
                  </>
                )}
              </div>
            </ScrollArea>
          </TabsContent>
          
          <TabsContent value="cryptopanic" className="mt-0">
            <div className="h-[400px]">
              <CryptoPanicWidget />
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}