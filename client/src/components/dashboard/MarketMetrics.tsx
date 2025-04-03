import { Card } from "@/components/ui/card";
import { TrendingUp, TrendingDown, Activity, DollarSign, BarChart3, BriefcaseIcon } from "lucide-react";

interface SonicToken {
  address?: string;
  symbol?: string;
  name?: string;
  decimals?: number;
  tvl?: number;
  tvlChange24h?: number;
  volume24h?: number;
  liquidity?: number;
  priceUsd?: number;
  priceChange24h?: number;
}

interface MarketSentiment {
  sentiment?: string;
  confidence?: number;
  trending?: { topic: string; volume: number }[];
}

interface FearGreedData {
  name: string;
  data: Array<{
    value: string;
    value_classification: string;
    timestamp: string;
    time_until_update?: string;
  }>;
}

interface DexVolumeData {
  volume24h: number;
  volumeChange24h: number;
}

interface MarketMetricsProps {
  sonicData?: SonicToken;
  sentimentData?: MarketSentiment;
  dexVolumeData?: DexVolumeData;
  fearGreedData?: FearGreedData;
  isLoading: boolean;
}

export function MarketMetrics({ sonicData, sentimentData, dexVolumeData, fearGreedData, isLoading }: MarketMetricsProps) {
  // Format currency for display
  const formatCurrency = (value?: number) => {
    if (!value) return "$0";
    
    if (value >= 1000000000) {
      return `$${(value / 1000000000).toFixed(2)}B`;
    } else if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(2)}M`;
    } else if (value >= 1000) {
      return `$${(value / 1000).toFixed(2)}K`;
    } else {
      return `$${value.toFixed(2)}`;
    }
  };
  
  // Get Fear & Greed value and classification for latest data
  const fearGreedValue = fearGreedData?.data?.[0]?.value || "45";
  const fearGreedClassification = fearGreedData?.data?.[0]?.value_classification || "Fear";
  
  // Map Fear & Greed classifications to colors
  const getFearGreedColor = (classification: string): string => {
    switch (classification.toLowerCase()) {
      case "extreme fear": return "text-red-600";
      case "fear": return "text-red-400";
      case "neutral": return "text-yellow-500";
      case "greed": return "text-green-400";
      case "extreme greed": return "text-green-600";
      default: return "text-neutral-500";
    }
  };

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Card 
            key={i} 
            className="p-4 bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5 h-24"
          >
            <div className="animate-pulse h-5 w-24 bg-muted rounded mb-4"></div>
            <div className="animate-pulse h-8 w-32 bg-muted rounded"></div>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Price Metric */}
      <Card className="p-4 bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <h3 className="text-sm text-muted-foreground mb-1 flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-primary" />
          SONIC Price
        </h3>
        <p className="text-2xl font-bold">${(sonicData?.priceUsd || 0).toFixed(4)}</p>
        <div className={`flex items-center gap-1 mt-1 ${
          (sonicData?.priceChange24h || 0) >= 0 ? 'text-green-500' : 'text-red-500'
        }`}>
          {(sonicData?.priceChange24h || 0) >= 0 ? 
            <TrendingUp className="h-4 w-4" /> : 
            <TrendingDown className="h-4 w-4" />
          }
          <span>{(sonicData?.priceChange24h || 0).toFixed(2)}%</span>
        </div>
      </Card>

      {/* Volume Metric - Now using DeFi Llama data for all DEXes */}
      <Card className="p-4 bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <h3 className="text-sm text-muted-foreground mb-1 flex items-center gap-2">
          <BarChart3 className="h-4 w-4 text-primary" />
          24h DEX Volume
        </h3>
        <p className="text-2xl font-bold">{formatCurrency(dexVolumeData?.volume24h || sonicData?.volume24h)}</p>
        <div className={`flex items-center gap-1 mt-1 ${
          (dexVolumeData?.volumeChange24h || 0) >= 0 ? 'text-green-500' : 'text-red-500'
        }`}>
          {(dexVolumeData?.volumeChange24h || 0) >= 0 ? 
            <TrendingUp className="h-4 w-4" /> : 
            <TrendingDown className="h-4 w-4" />
          }
          <span>{((dexVolumeData?.volumeChange24h || 0).toFixed(2))}%</span>
          <span className="text-xs text-muted-foreground ml-1">all pairs</span>
        </div>
      </Card>

      {/* TVL Metric */}
      <Card className="p-4 bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <h3 className="text-sm text-muted-foreground mb-1 flex items-center gap-2">
          <DollarSign className="h-4 w-4 text-primary" />
          Total Value Locked
        </h3>
        <p className="text-2xl font-bold">{formatCurrency(sonicData?.tvl)}</p>
        <div className={`flex items-center gap-1 mt-1 ${
          (sonicData?.tvlChange24h || 0) >= 0 ? 'text-green-500' : 'text-red-500'
        }`}>
          {(sonicData?.tvlChange24h || 0) >= 0 ? 
            <TrendingUp className="h-4 w-4" /> : 
            <TrendingDown className="h-4 w-4" />
          }
          <span>{(sonicData?.tvlChange24h || 0).toFixed(2)}%</span>
        </div>
      </Card>

      {/* Fear & Greed Metric */}
      <Card className="p-4 bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <h3 className="text-sm text-muted-foreground mb-1 flex items-center gap-2">
          <Activity className="h-4 w-4 text-primary" />
          Fear & Greed
        </h3>
        <p className="text-2xl font-bold flex items-center gap-2">
          <span>{fearGreedValue}</span>
          <span className={`text-base font-medium ${getFearGreedColor(fearGreedClassification)}`}>
            {fearGreedClassification}
          </span>
        </p>
        <div className="flex items-center gap-1 mt-1">
          <span className="text-xs text-muted-foreground">
            Market sentiment indicator
          </span>
        </div>
      </Card>
    </div>
  );
}