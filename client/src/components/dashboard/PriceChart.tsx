import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { cn } from "@/lib/utils";

interface PriceDataPoint {
  timestamp: string;
  price: number;
  volume: number;
}

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

interface PriceChartProps {
  className?: string;
  sonicData?: SonicToken;
  isLoading?: boolean;
  height?: string;
}

export function PriceChart({ className, sonicData, isLoading: externalLoading = false, height = '360px' }: PriceChartProps) {
  const [mounted, setMounted] = useState(false);
  const [timeframe, setTimeframe] = useState<string>("24h");

  // Only run queries after component has mounted
  useEffect(() => {
    setMounted(true);
  }, []);

  const { data: priceData, isLoading } = useQuery<PriceDataPoint[]>({
    queryKey: ['/api/market/prices', { token: 'SONIC', period: timeframe }],
    refetchInterval: 60000, // Refresh every minute
    enabled: mounted,
  });

  const formatXAxis = (timestamp: string) => {
    const date = new Date(timestamp);
    if (timeframe === "1h") {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (timeframe === "24h") {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (timeframe === "7d") {
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  const formatCurrency = (value: number) => {
    return `$${value.toFixed(4)}`;
  };

  if (!mounted || isLoading || externalLoading) {
    return (
      <Card className={cn("w-full bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5", className)}>
        <CardHeader>
          <CardTitle>Price Chart</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-[300px] flex items-center justify-center bg-primary/5 rounded-lg">
            <p className="text-muted-foreground">Loading price data...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={cn("w-full bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5", className)}>
      <CardHeader className="px-6 pt-6 pb-3">
        <div className="flex items-center">
          <CardTitle>SONIC Price & TVL</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="rounded-lg overflow-hidden" style={{ height }}>
          <iframe 
            title="DefiLlama Price and TVL Chart" 
            src="https://defillama.com/chart/chain/sonic?volume=false&perps=false&chainAssets=false&stables=false&chainTokenVolume=true&chainTokenMcap=true&chainTokenPrice=true&tvl=false" 
            width="100%" 
            height="100%" 
            frameBorder="0"
            loading="lazy"
          />
        </div>
      </CardContent>
    </Card>
  );
}