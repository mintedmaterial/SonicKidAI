import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ExternalLink, AlertCircle } from "lucide-react";

interface NewsItem {
  title: string;
  published_at: string;
  url: string;
  currencies?: { code: string; title: string; slug: string }[];
  source: { title: string; domain: string };
  description?: string;
  image?: string;
}

interface NewsResponse {
  results: NewsItem[];
}

interface SentimentData {
  sentiment: string;
  score: number;
  confidence: number;
  summary: string;
}

const TOKENS_TO_TRACK = [
  { value: "SONIC-3", label: "SONIC" },
  { value: "BTC", label: "Bitcoin" },
  { value: "ETH", label: "Ethereum" },
  { value: "SHADOW", label: "Shadow" }
];

export default function CryptoPanicWidget() {
  const [activeTab, setActiveTab] = useState(TOKENS_TO_TRACK[0].value);
  const [newsData, setNewsData] = useState<{ [key: string]: NewsItem[] }>({});
  const [sentiment, setSentiment] = useState<SentimentData | null>(null);
  const [trending, setTrending] = useState<NewsItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Fetch market sentiment
        const sentimentResponse = await fetch('/api/market/sentiment');
        if (!sentimentResponse.ok) {
          throw new Error('Error fetching sentiment');
        }
        const sentimentData = await sentimentResponse.json();
        setSentiment(sentimentData);

        // Fetch trending topics
        const trendingResponse = await fetch('/api/market/trending');
        if (!trendingResponse.ok) {
          throw new Error('Error fetching trending');
        }
        const trendingData = await trendingResponse.json();
        setTrending(trendingData.results || []);

        // Fetch news for each token
        const data: { [key: string]: NewsItem[] } = {};
        for (const token of TOKENS_TO_TRACK) {
          const response = await fetch(`/api/market/cryptopanic?currency=${token.value}`);
          if (!response.ok) {
            throw new Error(`Error fetching ${token.label} news: ${response.status}`);
          }
          const responseData: NewsResponse = await response.json();
          data[token.value] = responseData.results || [];
        }
        setNewsData(data);
      } catch (e) {
        console.error("Error fetching data:", e);
        setError("Unable to load data. Please try again later.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();

    // Refresh data every 15 minutes
    const interval = setInterval(fetchData, 15 * 60 * 1000);

    return () => clearInterval(interval);
  }, []);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  if (isLoading) {
    return (
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
    );
  }

  if (error) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <AlertCircle className="h-12 w-12 mx-auto mb-2 opacity-20" />
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div>
      {/* Market Sentiment Card */}
      {sentiment && (
        <Card className="mb-4 p-4 bg-background/70 border border-primary/10">
          <h2 className="text-lg font-medium">Market Sentiment</h2>
          <p>{sentiment.summary}</p>
          <p>Sentiment: {sentiment.sentiment} (Score: {sentiment.score}, Confidence: {sentiment.confidence}%)</p>
        </Card>
      )}

      {/* Trending Topics Card */}
      {trending.length > 0 && (
        <Card className="mb-4 p-4 bg-background/70 border border-primary/10">
          <h2 className="text-lg font-medium">Trending Topics</h2>
          <ul>
            {trending.map((item, index) => (
              <li key={index} className="mb-2">
                <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary/80">
                  {item.title}
                </a>
              </li>
            ))}
          </ul>
        </Card>
      )}

      {/* News Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="w-full mb-4 grid grid-cols-4">
          {TOKENS_TO_TRACK.map((token) => (
            <TabsTrigger key={token.value} value={token.value}>
              {token.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {TOKENS_TO_TRACK.map((token) => (
          <TabsContent key={token.value} value={token.value} className="mt-0">
            <ScrollArea className="h-[350px] pr-4">
              <div className="space-y-4">
                {newsData[token.value]?.length > 0 ? (
                  newsData[token.value].map((item, index) => (
                    <Card key={index} className="p-4 bg-background/70 border border-primary/10 hover:bg-background/80 transition-colors">
                      {item.image && <img src={item.image} alt={item.title} className="w-full h-32 object-cover rounded mb-2" />}
                      <div className="mb-2 flex justify-between items-start">
                        <h3 className="font-medium">{item.title}</h3>
                        <Badge variant="outline" className="ml-2 shrink-0">
                          {token.label}
                        </Badge>
                      </div>
                      {item.description && <p className="text-sm text-muted-foreground mb-2">{item.description.substring(0, 100)}...</p>}
                      <div className="flex justify-between items-center text-sm">
                        <p className="text-muted-foreground">{item.source.title}</p>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">
                            {formatDate(item.published_at)}
                          </span>
                          <a href={item.url} target="_blank" rel="noopener noreferrer" className="text-primary hover:text-primary/80">
                            <ExternalLink className="h-3 w-3" />
                          </a>
                        </div>
                      </div>
                    </Card>
                  ))
                ) : (
                  <div className="text-center py-8 text-muted-foreground">
                    <p>No news available for {token.label}</p>
                  </div>
                )}
              </div>
            </ScrollArea>
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}