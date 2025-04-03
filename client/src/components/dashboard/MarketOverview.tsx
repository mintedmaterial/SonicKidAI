import { useEffect, useState, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  Activity, 
  BarChart3, 
  LineChart, 
  TrendingUp, 
  TrendingDown, 
  DollarSign 
} from "lucide-react";

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
  nativeAddress?: string;
  wrappedAddress: string;
  decimals: number;
  priceUsd: number;
  priceChange24h: number;
  volume24h: number;
  volumeChange24h: number;
  tvl: number;
  tvlChange24h: number;
  chain: string;
}

interface DexVolumeData {
  volume24h: number;
  volumeChange24h: number;
}

interface DexVolumeResponse {
  success: boolean;
  data: DexVolumeData;
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

export function MarketOverview() {
  const [mounted, setMounted] = useState(false);
  const queryClient = useQueryClient();
  
  // Force refresh of data at regular intervals - different frequencies for different data types
  useEffect(() => {
    // Sonic price refresh - every 20 seconds (3x per minute)
    const sonicRefreshInterval = setInterval(() => {
      console.log("Forcing Sonic price data refresh...");
      queryClient.invalidateQueries({ queryKey: ['/data/sonic'] });
    }, 20000);
    
    // Other data refresh - less frequent (every 60 seconds)
    const otherDataRefreshInterval = setInterval(() => {
      console.log("Forcing other market data refresh...");
      queryClient.invalidateQueries({ queryKey: ['/api/market/sentiment'] });
      queryClient.invalidateQueries({ queryKey: ['/api/market/news'] });
      queryClient.invalidateQueries({ queryKey: ['/api/market/dex-volume'] });
    }, 60000);
    
    return () => {
      clearInterval(sonicRefreshInterval);
      clearInterval(otherDataRefreshInterval);
    };
  }, [queryClient]);

  // Only run queries after component has mounted
  useEffect(() => {
    setMounted(true);
    
    // Immediately force a refresh when component mounts
    queryClient.invalidateQueries({ queryKey: ['/data/sonic'] });
  }, [queryClient]);

  // Query for Sonic TVL data
  // Use direct data endpoint to bypass SPA middleware issues
  const { data: sonicData, isLoading: sonicLoading } = useQuery<SonicToken>({
    queryKey: ['/data/sonic'],
    refetchInterval: 20000, // Refresh every 20 seconds for fresher data (3x per minute)
    enabled: mounted,
  });

  // Query for sentiment data from our Hugging Face integration
  const { data: sentimentData, isLoading: sentimentLoading } = useQuery<MarketSentiment>({
    queryKey: ['/api/market/sentiment'],
    refetchInterval: 60000, // Refresh every minute
    enabled: mounted,
  });

  // Query for market news
  const { data: newsData, isLoading: newsLoading } = useQuery<MarketNews>({
    queryKey: ['/api/market/news'],
    refetchInterval: 60000, // Refresh every minute
    enabled: mounted,
  });

  // Query for DEX volume data
  const { data: dexVolumeData, isLoading: dexVolumeLoading } = useQuery<DexVolumeResponse>({
    queryKey: ['/api/market/dex-volume'],
    refetchInterval: 300000, // Refresh every 5 minutes
    enabled: mounted,
  });

  if (!mounted || sonicLoading || sentimentLoading || dexVolumeLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[1, 2, 3].map((i) => (
          <Card 
            key={i} 
            className="p-4 bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5 h-48"
          >
            <div className="animate-pulse h-5 w-24 bg-muted rounded mb-4"></div>
            <div className="animate-pulse h-8 w-32 bg-muted rounded mb-2"></div>
            <div className="animate-pulse h-4 w-20 bg-muted rounded"></div>
          </Card>
        ))}
      </div>
    );
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
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Sentiment Card */}
      <Card className="p-4 bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <h3 className="text-sm text-muted-foreground mb-1 flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          Market Sentiment
        </h3>
        <p className="text-2xl font-bold">{sentimentData?.sentiment || 'Neutral'}</p>
        <div className="flex items-center gap-1 mt-1">
          <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10">
            {sentimentData?.confidence || 0}% confidence
          </span>
        </div>
      </Card>

      {/* Volume Card */}
      <Card className="p-4 bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <h3 className="text-sm text-muted-foreground mb-1 flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-primary" />
          Sonic Volume (24h)
        </h3>
        <p className="text-2xl font-bold">{dexVolumeData?.data ? formatCurrency(dexVolumeData.data.volume24h) : '$220.57M'}</p>
        <div className={`flex items-center gap-1 mt-1 ${
          (dexVolumeData?.data?.volumeChange24h || 0) >= 0 ? 'text-green-500' : 'text-red-500'
        }`}>
          {(dexVolumeData?.data?.volumeChange24h || 0) >= 0 ? 
            <TrendingUp className="h-4 w-4" /> : 
            <TrendingDown className="h-4 w-4" />
          }
          <span>{(dexVolumeData?.data?.volumeChange24h || 0).toFixed(2)}%</span>
        </div>
      </Card>

      {/* TVL Card */}
      <Card className="p-4 bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <h3 className="text-sm text-muted-foreground mb-1 flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-primary" />
          Total Value Locked
        </h3>
        <p className="text-2xl font-bold">${(sonicData?.tvl || 0).toLocaleString()}</p>
        <div className={`flex items-center gap-1 mb-2 ${
          (sonicData?.tvlChange24h || 0) >= 0 ? 'text-green-500' : 'text-red-500'
        }`}>
          {(sonicData?.tvlChange24h || 0) >= 0 ? 
            <TrendingUp className="h-4 w-4" /> : 
            <TrendingDown className="h-4 w-4" />
          }
          <span>{(sonicData?.tvlChange24h || 0).toFixed(2)}%</span>
        </div>
        
        {/* No chart here as requested */}
      </Card>

      {/* Price Card - Spans Full Width */}
      <Card className="p-4 bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5 md:col-span-3">
        <div className="flex justify-between mb-3">
          <div>
            <h3 className="text-sm text-muted-foreground mb-1 flex items-center gap-2">
              <LineChart className="h-4 w-4 text-primary" />
              <div className="flex items-center">
                <span>Sonic Price/Marketcap/Volume</span>
                <img 
                  src="/wS_token_400.png" 
                  alt="Sonic Logo" 
                  className="ml-2 h-5 w-5" 
                />
              </div>
            </h3>
            <p className="text-2xl font-bold">${(sonicData?.priceUsd || 0).toFixed(4)}</p>
            <div className={`flex items-center gap-1 ${
              (sonicData?.priceChange24h || 0) >= 0 ? 'text-green-500' : 'text-red-500'
            }`}>
              {(sonicData?.priceChange24h || 0) >= 0 ? 
                <TrendingUp className="h-4 w-4" /> : 
                <TrendingDown className="h-4 w-4" />
              }
              <span>{(sonicData?.priceChange24h || 0).toFixed(2)}%</span>
            </div>
          </div>
          <div className="text-right">
            <span className="text-xs text-muted-foreground">Chain</span>
            <p className="font-medium">{sonicData?.chain || 'Fantom'}</p>
          </div>
        </div>

        {/* DefiLlama Price & TVL Chart */}
        <div className="mt-2 rounded-lg overflow-hidden" style={{ height: '360px' }}>
          <iframe 
            title="DefiLlama Sonic Chart" 
            src="https://defillama.com/chart/chain/sonic?volume=false&perps=false&chainAssets=false&stables=false&chainTokenVolume=true&chainTokenMcap=true&chainTokenPrice=true&tvl=false" 
            width="100%" 
            height="100%" 
            frameBorder="0"
            loading="lazy"
            style={{ border: 'none' }}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        </div>
      </Card>

      {/* Token Details */}
      <Card className="p-4 bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5 md:col-span-3">
        <h3 className="text-sm font-medium mb-3">Token Details</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-xs text-muted-foreground block">Name</span>
            <span className="font-medium">{sonicData?.name || 'Wrapped Sonic'}</span>
          </div>
          <div>
            <span className="text-xs text-muted-foreground block">Symbol</span>
            <span className="font-medium">{sonicData?.symbol || 'wS'}</span>
          </div>
          <div>
            <span className="text-xs text-muted-foreground block">Native Address</span>
            <span className="font-medium truncate">
              {sonicData?.address || '0x039e2fb66102314ce7b64ce5ce3e5183bc94ad38'}
            </span>
          </div>
          <div>
            <span className="text-xs text-muted-foreground block">Wrapped Address</span>
            <span className="font-medium truncate">
              {sonicData?.wrappedAddress || '0x039e2fb66102314ce7b64ce5ce3e5183bc94ad38'}
            </span>
          </div>
          <div>
            <span className="text-xs text-muted-foreground block">Decimals</span>
            <span className="font-medium">{sonicData?.decimals || 18}</span>
          </div>
          <div>
            <span className="text-xs text-muted-foreground block">Chain</span>
            <span className="font-medium">{sonicData?.chain || 'Sonic'}</span>
          </div>
        </div>
      </Card>
    </div>
  );
}