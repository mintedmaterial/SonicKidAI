import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useQuery } from "@tanstack/react-query";
import { 
  Activity, 
  Newspaper, 
  TrendingUp, 
  TrendingDown, 
  BarChart3,
  LineChart,
  Zap
} from "lucide-react";
import { MarketMetrics } from "@/components/dashboard/MarketMetrics";
import { PriceChart } from "@/components/dashboard/PriceChart";
import { NewsFeed } from "@/components/dashboard/NewsFeed"; 
import { TradingActivity } from "@/components/dashboard/TradingActivity";
import { WalletOverview } from "@/components/dashboard/WalletOverview";
import { NetworkStats } from "@/components/dashboard/NetworkStats";
import { NFTSales } from "@/components/dashboard/NFTSales";
import { FearGreedChart } from "@/components/dashboard/FearGreedChart";
import { TheGraphData } from "@/components/dashboard/TheGraphData";

export function EnhancedDashboard() {
  const [mounted, setMounted] = useState(false);

  // Only render the dashboard after it has mounted
  // This prevents hydration issues
  useEffect(() => {
    setMounted(true);
  }, []);

  // Interface definitions for API responses
  interface SonicToken {
    address: string;
    symbol: string;
    name: string;
    decimals: number;
    tvl: number;
    tvlChange24h: number;
    volume24h: number;
    liquidity: number;
    priceUsd?: number;
    priceChange24h?: number;
  }
  
  interface DexVolumeDataResponse {
    success: boolean;
    data: {
      volume24h: number;
      volumeChange24h: number;
    };
  }

  interface MarketSentiment {
    sentiment: string;
    confidence: number;
    trending: { topic: string; volume: number }[];
  }

  interface NewsArticle {
    title: string;
    source: string;
    time: string;
  }

  interface MarketNews {
    articles: NewsArticle[];
  }

  const { data: sonicData, isLoading: sonicLoading } = useQuery<SonicToken>({
    queryKey: ['/api/market/sonic'],
    refetchInterval: 300000, // Refresh every 5 minutes
    enabled: mounted
  });

  // Query for sentiment data
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
  
  // Query for DEX volume data from DeFi Llama
  const { data: dexVolumeData, isLoading: dexVolumeLoading } = useQuery<DexVolumeDataResponse>({
    queryKey: ['/api/market/dex-volume'],
    refetchInterval: 300000, // Refresh every 5 minutes
    enabled: mounted
  });

  if (!mounted) {
    return <div className="min-h-screen bg-background"></div>;
  }

  return (
    <div className="min-h-screen bg-black bg-gradient-to-b from-black to-background">
      <div className="absolute inset-0 bg-[url('/market_visualization_1740761270.png')] bg-no-repeat bg-center bg-contain opacity-20 pointer-events-none"></div>
      <div className="container mx-auto py-6 px-4 space-y-6 relative z-10">
        <div className="mb-6">
          <h1 className="text-3xl font-bold tracking-tight">
            <span className="text-pink-500">SonicKid</span> <span className="text-primary">AI</span> Dashboard
          </h1>
          <p className="text-muted-foreground mt-1">
            Cross-chain analytics and trading insights
          </p>
        </div>

        {/* Top metrics overview */}
        <MarketMetrics 
          sonicData={sonicData} 
          sentimentData={sentimentData}
          dexVolumeData={dexVolumeData?.data}
          isLoading={sonicLoading || sentimentLoading || dexVolumeLoading} 
        />
        
        {/* Price chart and network stats sections */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Card className="h-full bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
              <div className="p-4">
                <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
                  <LineChart className="h-5 w-5 text-primary" />
                  <div className="flex items-center">
                    <span>TVL & Volume Analysis</span>
                    <img 
                      src="/wS_token_400.png" 
                      alt="Sonic Logo" 
                      className="ml-2 h-6 w-6" 
                    />
                  </div>
                </h2>
                <div className="w-full overflow-hidden rounded-md">
                  <iframe 
                    width="100%" 
                    height="360px" 
                    src="https://defillama.com/chart/chain/sonic?volume=true&perps=false&chainAssets=true&stables=false&chainTokenVolume=true&chainTokenMcap=true&chainTokenPrice=true&tvl=true" 
                    title="DefiLlama Sonic Chart" 
                    frameBorder="0"
                    loading="lazy"
                    className="bg-white/5 rounded-md"
                  ></iframe>
                </div>
              </div>
            </Card>
          </div>
          <div className="space-y-6">
            <NetworkStats 
              sonicData={sonicData} 
              isLoading={sonicLoading} 
            />
            {/* Fear & Greed Chart (Smaller version) */}
            <Card className="p-4 bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
              <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                Fear & Greed Index
              </h3>
              <div className="flex justify-center">
                <img 
                  src="https://alternative.me/crypto/fear-and-greed-index.png" 
                  alt="Latest Crypto Fear & Greed Index" 
                  className="w-full max-w-[250px] h-auto"
                  loading="lazy"
                />
              </div>
              <div className="mt-2 text-xs text-muted-foreground text-center">
                <p>Data from <a href="https://alternative.me/" target="_blank" rel="noopener noreferrer" className="underline hover:text-primary">Alternative.me</a></p>
              </div>
            </Card>
          </div>
        </div>
        
        {/* NFT Sales section */}
        <div className="mt-6">
          <NFTSales />
        </div>
        
        {/* The Graph Protocol Data - Sonic Exchange Data */}
        <div className="mt-6">
          <TheGraphData />
        </div>

        {/* Tabbed section for different content types */}
        <Tabs defaultValue="news" className="w-full mt-6">
          <TabsList className="mb-4">
            <TabsTrigger value="news">Market News</TabsTrigger>
            <TabsTrigger value="trading">Trading Activity</TabsTrigger>
            <TabsTrigger value="wallet">Wallet Overview</TabsTrigger>
          </TabsList>
          
          <TabsContent value="news" className="space-y-4 pt-2">
            <NewsFeed newsData={newsData} isLoading={newsLoading} />
          </TabsContent>
          
          <TabsContent value="trading" className="space-y-4 pt-2">
            <TradingActivity />
          </TabsContent>
          
          <TabsContent value="wallet" className="space-y-4 pt-2">
            <WalletOverview />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}

export default EnhancedDashboard;