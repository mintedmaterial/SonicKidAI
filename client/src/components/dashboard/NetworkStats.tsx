import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Database, Layers, Wallet, Network } from "lucide-react";

interface NetworkStatsProps {
  sonicData?: {
    address?: string;
    symbol?: string;
    name?: string;
    tvl?: number;
    tvlChange24h?: number;
    volume24h?: number;
    liquidity?: number;
  };
  isLoading?: boolean;
}

export function NetworkStats({ sonicData, isLoading }: NetworkStatsProps) {
  // Format currency for display
  const formatCurrency = (value: number | undefined) => {
    if (!value) return "$0";
    
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(2)}M`;
    } else if (value >= 1000) {
      return `$${(value / 1000).toFixed(2)}K`;
    } else {
      return `$${value.toFixed(2)}`;
    }
  };

  if (isLoading) {
    return (
      <Card className="bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Network className="h-5 w-5 text-primary" />
            Network Stats
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="bg-primary/10 p-2 rounded-md">
                  <div className="animate-pulse h-5 w-5 bg-muted rounded"></div>
                </div>
                <div className="flex-1">
                  <div className="animate-pulse h-4 w-24 bg-muted rounded mb-1"></div>
                  <div className="animate-pulse h-6 w-32 bg-muted rounded"></div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  const stats = [
    {
      icon: <Database className="h-5 w-5 text-primary" />,
      name: "Total Value Locked",
      value: formatCurrency(sonicData?.tvl),
      change: sonicData?.tvlChange24h ? `${sonicData.tvlChange24h.toFixed(2)}%` : "0%",
      isPositive: (sonicData?.tvlChange24h || 0) >= 0
    },
    {
      icon: <Layers className="h-5 w-5 text-primary" />,
      name: "Liquidity",
      value: formatCurrency(sonicData?.liquidity),
      secondaryText: "Across pairs"
    },
    {
      icon: <Wallet className="h-5 w-5 text-primary" />,
      name: "Contract Address",
      value: sonicData?.address ? `${sonicData.address.slice(0, 6)}...${sonicData.address.slice(-4)}` : "0x000...0000",
      secondaryText: "Verified"
    },
    {
      icon: <Network className="h-5 w-5 text-primary" />,
      name: "Network",
      value: "Sonic",
      secondaryText: "Chain ID: 146"
    }
  ];

  return (
    <Card className="bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <Network className="h-5 w-5 text-primary" />
          Network Stats
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {stats.map((stat, index) => (
            <div key={index} className="flex items-start gap-3">
              <div className="bg-primary/10 p-2 rounded-md">
                {stat.icon}
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{stat.name}</p>
                <div className="flex items-baseline gap-2">
                  <p className="text-lg font-medium">{stat.value}</p>
                  {stat.change && (
                    <span className={stat.isPositive ? "text-green-500 text-xs" : "text-red-500 text-xs"}>
                      {stat.change}
                    </span>
                  )}
                </div>
                {stat.secondaryText && (
                  <p className="text-xs text-muted-foreground mt-0.5">{stat.secondaryText}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}