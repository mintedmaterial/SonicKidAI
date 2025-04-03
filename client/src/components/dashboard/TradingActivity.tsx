import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ArrowUp, ArrowDown, CircleDollarSign, CircleAlert, CheckCircle } from "lucide-react";

// Define types inline
interface TradingActivity {
  id: number;
  timestamp: string;
  status: string;
  actionType: string;
  fromToken: string;
  toToken: string;
  fromAmount: number;
  toAmount: number;
  chainId: string;
  platform: string;
  txHash: string;
  metadata: any;
}

export function TradingActivity() {
  const [mounted, setMounted] = useState(false);

  // Only run queries after component has mounted
  useEffect(() => {
    setMounted(true);
  }, []);

  // Simulated trading activity data
  const tradingActivities: TradingActivity[] = [
    {
      id: 1,
      timestamp: new Date(Date.now() - 12 * 60 * 1000).toISOString(), // 12 minutes ago
      status: "completed",
      actionType: "swap",
      fromToken: "SONIC",
      toToken: "WETH",
      fromAmount: 250,
      toAmount: 0.12,
      chainId: "146",
      platform: "SonicSwap",
      txHash: "0xabc123...",
      metadata: { gasPrice: "20 Gwei", gasUsed: 250000 }
    },
    {
      id: 2,
      timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(), // 45 minutes ago
      status: "completed",
      actionType: "swap",
      fromToken: "USDC",
      toToken: "SONIC",
      fromAmount: 500,
      toAmount: 350.25,
      chainId: "146",
      platform: "SonicSwap",
      txHash: "0xdef456...",
      metadata: { gasPrice: "18 Gwei", gasUsed: 220000 }
    },
    {
      id: 3,
      timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(), // 3 hours ago
      status: "pending",
      actionType: "bridge",
      fromToken: "SONIC",
      toToken: "SONIC",
      fromAmount: 1000,
      toAmount: 998.5,
      chainId: "146",
      platform: "Connext",
      txHash: "0xghi789...",
      metadata: { destinationChain: "Fantom", fee: 1.5 }
    },
    {
      id: 4,
      timestamp: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(), // 8 hours ago
      status: "failed",
      actionType: "swap",
      fromToken: "WETH",
      toToken: "USDC",
      fromAmount: 0.5,
      toAmount: 0,
      chainId: "146",
      platform: "SonicSwap",
      txHash: "0xjkl101...",
      metadata: { error: "Slippage exceeded" }
    }
  ];

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-500/10 text-green-500 border-green-500/20";
      case "pending":
        return "bg-yellow-500/10 text-yellow-500 border-yellow-500/20";
      case "failed":
        return "bg-red-500/10 text-red-500 border-red-500/20";
      default:
        return "bg-gray-500/10 text-gray-500 border-gray-500/20";
    }
  };

  const getActionIcon = (actionType: string) => {
    switch (actionType) {
      case "swap":
        return <ArrowUp className="h-4 w-4 mr-1" />;
      case "bridge":
        return <CircleDollarSign className="h-4 w-4 mr-1" />;
      default:
        return <CircleAlert className="h-4 w-4 mr-1" />;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 mr-1" />;
      case "pending":
        return <CircleAlert className="h-4 w-4 mr-1" />;
      case "failed":
        return <CircleAlert className="h-4 w-4 mr-1" />;
      default:
        return <CircleAlert className="h-4 w-4 mr-1" />;
    }
  };

  if (!mounted) {
    return (
      <Card className="w-full bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <CardHeader>
          <CardTitle>Trading Activity</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-[300px]">
            <p className="text-muted-foreground">Loading trading activity...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
      <CardHeader>
        <CardTitle>Trading Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {tradingActivities.map((activity) => (
            <div 
              key={activity.id} 
              className="flex items-center p-3 rounded-lg border border-primary/10 bg-background/70"
            >
              <div className="mr-4">
                {getActionIcon(activity.actionType)}
              </div>
              <div className="flex-1">
                <div className="flex justify-between">
                  <p className="font-medium">
                    {activity.actionType === "swap" 
                      ? `Swap ${activity.fromToken} to ${activity.toToken}` 
                      : `Bridge ${activity.fromToken} to ${activity.toToken}`}
                  </p>
                  <Badge variant="outline" className={getStatusColor(activity.status)}>
                    <span className="flex items-center">
                      {getStatusIcon(activity.status)}
                      {activity.status}
                    </span>
                  </Badge>
                </div>
                <div className="flex justify-between mt-1">
                  <p className="text-sm text-muted-foreground">
                    {activity.fromAmount} {activity.fromToken} 
                    {activity.actionType === "swap" ? " → " : " ⟷ "} 
                    {activity.toAmount} {activity.toToken}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(activity.timestamp)} {formatTime(activity.timestamp)}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}