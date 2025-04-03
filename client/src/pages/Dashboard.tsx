import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { DashboardFeed } from "@/components/DashboardFeed";
import { useQuery } from "@tanstack/react-query";
import { 
  Activity, 
  Newspaper, 
  TrendingUp, 
  TrendingDown, 
  DollarSign, 
  BarChart3,
  LineChart,
  PieChart,
  Zap,
  Twitter,
  Bot
} from "lucide-react";
import { MarketOverview } from "@/components/dashboard/MarketOverview";
import { MarketMetrics } from "@/components/dashboard/MarketMetrics";
import { FearGreedChart } from "@/components/dashboard/FearGreedChart";
import { TwitterFeed } from "@/components/dashboard/TwitterFeed";
import SonicPairs from "@/components/dashboard/SonicPairs";
import { AdSpace } from "@/components/dashboard/AdSpace";
import { AgentMonitoring } from "@/components/dashboard/AgentMonitoring";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DexPairToken } from "@shared/marketdata";

export function Dashboard() {
  const [mounted, setMounted] = useState(false);

  // Only render the dashboard after it has mounted
  // This prevents hydration issues
  useEffect(() => {
    setMounted(true);
  }, []);

  // Define types inline to avoid directory creation issues
  interface TrendingTopic {
    topic: string;
    volume: number;
  }

  interface MarketSentiment {
    sentiment: string;
    confidence: number;
    trending?: TrendingTopic[];
  }

  interface SonicToken {
    name: string;
    symbol: string;
    address: string;
    decimals: number;
    priceUsd: number;
    priceChange24h: number;
    volume24h: number;
    volumeChange24h: number;
    tvl: number;
    tvlChange24h: number;
    chain: string;
  }

  interface NewsArticle {
    title: string;
    source: string;
    time: string;
    url?: string;
  }

  interface MarketNews {
    articles: NewsArticle[];
  }

  // Query for Sonic TVL data
  const { data: sonicData, isLoading: sonicLoading } = useQuery<SonicToken>({
    queryKey: ['/api/market/sonic'],
    refetchInterval: 300000, // Refresh every 5 minutes
    enabled: mounted
  });

  // Query for sentiment data from our Hugging Face integration
  const { data: sentimentData, isLoading: sentimentLoading } = useQuery<MarketSentiment>({
    queryKey: ['/api/market/sentiment'],
    refetchInterval: 60000, // Refresh every minute
    enabled: mounted
  });

  // Query for market news
  const { data: newsData, isLoading: newsLoading } = useQuery<MarketNews>({
    queryKey: ['/api/market/news'],
    refetchInterval: 60000, // Refresh every minute
    enabled: mounted
  });
  
  // Query for Sonic pairs data from DexScreener using direct data endpoint
  const { data: sonicPairsResponse, isLoading: sonicPairsLoading, error: sonicPairsError } = useQuery<{success: boolean, data: any[]}>({
    queryKey: ['/data/sonic-pairs.json'], // Direct endpoint that bypasses SPA middleware completely
    refetchInterval: 300000, // Refresh every 5 minutes
    enabled: mounted
  });
  
  // Define interfaces for our query results
  interface DexVolumeDataResponse {
    success: boolean;
    data: {
      volume24h: number;
      volumeChange24h: number;
    };
  }

  // Query for DEX volume data from DeFi Llama
  const { data: dexVolumeData, isLoading: dexVolumeLoading } = useQuery<DexVolumeDataResponse>({
    queryKey: ['/api/market/dex-volume'],
    refetchInterval: 300000, // Refresh every 5 minutes
    enabled: mounted
  });
  
  // Define interface for Fear and Greed data
  interface FearGreedResponse {
    success: boolean;
    data: {
      name: string;
      data: Array<{
        value: string;
        value_classification: string;
        timestamp: string;
        time_until_update?: string;
      }>;
    };
  }
  
  // Query for Fear and Greed data
  const { data: fearGreedData, isLoading: fearGreedLoading } = useQuery<FearGreedResponse>({
    queryKey: ['/api/market/fear-greed'],
    refetchInterval: 3600000, // Refresh every hour
    enabled: mounted
  });
  
  // Define interface for Project of the Week data
  interface ProjectOfWeek {
    name: string;
    description: string;
    tokenSymbol: string;
    artworkUrl: string;
    price: number;
    priceChange24h: number;
    volume24h: number;
    liquidity: number;
    pairAddress: string;
    chain: string;
    website?: string;
  }
  
  // Query for Project of the Week data
  const { data: projectOfWeekData, isLoading: projectOfWeekLoading } = useQuery<ProjectOfWeek>({
    queryKey: ['/data/project-of-week'],
    refetchInterval: 600000, // Refresh every 10 minutes
    enabled: mounted
  });

  if (!mounted) {
    return <div className="min-h-screen bg-background"></div>;
  }

  // Format currency for display
  const formatCurrency = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(2)}M`;
    } else if (value >= 1000) {
      return `$${(value / 1000).toFixed(2)}K`;
    } else {
      return `$${value.toFixed(2)}`;
    }
  };

  return (
    <div className="min-h-screen bg-black bg-gradient-to-b from-black to-background">
      <div className="absolute inset-0 bg-[url('/market_visualization_1740761270.png')] bg-no-repeat bg-center bg-contain opacity-10 pointer-events-none"></div>
      <div className="container mx-auto p-4 space-y-6 relative z-10">
        <div className="mb-4">
          <h1 className="text-2xl font-bold">
            <span className="text-pink-500">SonicKid</span> <span className="text-primary">AI</span> Dashboard
          </h1>
          <p className="text-muted-foreground">Market intelligence and agent activity</p>
        </div>

        {/* Market Metrics Section */}
        <MarketMetrics 
          sonicData={sonicData} 
          sentimentData={sentimentData} 
          dexVolumeData={dexVolumeData?.data}
          fearGreedData={fearGreedData?.data}
          isLoading={sonicLoading || sentimentLoading || dexVolumeLoading || fearGreedLoading} 
        />
        
        {/* Market Overview Section */}
        <MarketOverview />

        {/* Fear & Greed Widget Section */}
        <div className="w-full">
          <FearGreedChart height="350px" />
        </div>

        {/* Market Content Tabs */}
        <Tabs defaultValue="news" className="w-full">
          <TabsList className="mb-4">
            <TabsTrigger value="news">Market News</TabsTrigger>
            <TabsTrigger value="social">Social</TabsTrigger>
            <TabsTrigger value="activity">Agent Activity</TabsTrigger>
            <TabsTrigger value="monitoring"><div className="flex items-center gap-1"><Bot className="h-4 w-4" />Agent Monitoring</div></TabsTrigger>
          </TabsList>
          
          <TabsContent value="news" className="space-y-4">
            <Card className="bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
              <div className="p-4">
                <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
                  <Newspaper className="h-5 w-5 text-primary" />
                  Latest Market News
                </h2>
                <ScrollArea className="h-[400px] pr-4">
                  <div className="space-y-4">
                    {newsLoading ? (
                      <p>Loading news...</p>
                    ) : (
                      newsData?.articles?.map((article: any, index: number) => (
                        <Card key={index} className="p-4 bg-background/70 border border-primary/10 mb-4">
                          <p className="font-medium mb-1">{article.title}</p>
                          <div className="flex justify-between items-center mt-2">
                            <p className="text-sm text-muted-foreground">
                              {article.source}
                            </p>
                            <p className="text-xs text-muted-foreground">
                              {article.time}
                            </p>
                          </div>
                        </Card>
                      ))
                    )}
                  </div>
                </ScrollArea>
              </div>
            </Card>
          </TabsContent>
          
          <TabsContent value="social" className="space-y-4">
            <TwitterFeed />
          </TabsContent>
          
          <TabsContent value="activity" className="space-y-4">
            <DashboardFeed />
          </TabsContent>
          
          <TabsContent value="monitoring" className="space-y-4">
            <AgentMonitoring />
          </TabsContent>
        </Tabs>


        
        {/* Project of the Week - Ad Space Section */}
        <div className="w-full">
          <AdSpace 
            projectData={projectOfWeekData}
            isLoading={projectOfWeekLoading}
          />
        </div>
        
        {/* Sonic Pairs Section */}
        <div className="w-full">
          <SonicPairs 
            pairsData={sonicPairsResponse?.data} 
            isLoading={sonicPairsLoading} 
            error={sonicPairsError as Error|null} 
          />
        </div>
      </div>
    </div>
  );
}

export default Dashboard;