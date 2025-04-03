import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Wallet, Copy, ExternalLink, CheckCircle, AlertCircle, ArrowRightLeft, Plus } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

interface TokenBalance {
  symbol: string;
  name: string;
  balance: number;
  usdValue: number;
  tokenAddress: string;
}

export function WalletOverview() {
  const [walletAddress, setWalletAddress] = useState<string>("");
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isCopied, setIsCopied] = useState<boolean>(false);

  // Mock wallet balances for visual demo
  const tokenBalances: TokenBalance[] = [
    {
      symbol: "SONIC",
      name: "Sonic",
      balance: 1250.5,
      usdValue: 1750.7,
      tokenAddress: "0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38"
    },
    {
      symbol: "wS",
      name: "Wrapped Sonic",
      balance: 550.25,
      usdValue: 770.35,
      tokenAddress: "0x7f5373AE26c3E8FfC4c77b7255DF7eC1A9aF52a6"
    },
    {
      symbol: "WETH",
      name: "Wrapped Ethereum",
      balance: 0.75,
      usdValue: 2400,
      tokenAddress: "0x82af49447d8a07e3bd95bd0d56f35241523fbab1"
    },
    {
      symbol: "USDT",
      name: "Tether USD",
      balance: 1500,
      usdValue: 1500,
      tokenAddress: "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9"
    }
  ];

  // Set a sample address immediately for display purposes
  const sampleAddress = "0xCC98d2e64279645D204DD7b25A7c09b6B3ded0d9";

  const handleConnect = async () => {
    setIsLoading(true);
    
    // Simulate connection delay
    setTimeout(() => {
      setWalletAddress(walletAddress || sampleAddress);
      setIsConnected(true);
      setIsLoading(false);
    }, 1000);
  };

  const handleCopyAddress = () => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(walletAddress || sampleAddress);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  const formatBalance = (balance: number) => {
    return balance.toLocaleString(undefined, { 
      minimumFractionDigits: 2,
      maximumFractionDigits: 6
    });
  };

  const formatUsd = (value: number) => {
    return value.toLocaleString(undefined, { 
      style: 'currency', 
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    });
  };

  const getTotalValue = () => {
    return tokenBalances.reduce((sum, token) => sum + token.usdValue, 0);
  };

  return (
    <Card className="bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Wallet className="h-5 w-5 text-primary" />
          Wallet Overview
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!isConnected ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <label htmlFor="wallet-address" className="text-sm font-medium">
                Wallet Address
              </label>
              <Input
                id="wallet-address"
                placeholder="0x..."
                value={walletAddress}
                onChange={(e) => setWalletAddress(e.target.value)}
              />
            </div>
            <Button 
              onClick={handleConnect} 
              className="w-full" 
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-background border-r-transparent"></span>
                  Connecting...
                </>
              ) : (
                <>
                  Connect Wallet
                </>
              )}
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <label className="text-sm text-muted-foreground">
                  Connected Wallet
                </label>
                <Badge variant="outline" className="px-2 py-0">Sonic Chain</Badge>
              </div>
              <div className="flex items-center gap-2 bg-background/80 p-2 rounded-md border border-primary/10">
                <span className="text-sm font-mono truncate flex-1">
                  {walletAddress}
                </span>
                <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleCopyAddress}>
                  {isCopied ? <CheckCircle className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                </Button>
                <Button variant="ghost" size="icon" className="h-6 w-6" asChild>
                  <a
                    href={`https://explorer.sonic.wiki/address/${walletAddress}`}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink className="h-4 w-4" />
                  </a>
                </Button>
              </div>
            </div>
            
            <div>
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-muted-foreground">Total Balance</span>
                <span className="text-lg font-semibold">{formatUsd(getTotalValue())}</span>
              </div>
              
              <ScrollArea className="h-[300px] pr-4">
                <div className="space-y-3">
                  {tokenBalances.map((token) => (
                    <Card key={token.symbol} className="p-3 bg-background/70 border border-primary/10">
                      <div className="flex justify-between items-center">
                        <div>
                          <div className="font-medium">{token.symbol}</div>
                          <div className="text-xs text-muted-foreground">{token.name}</div>
                        </div>
                        <div className="text-right">
                          <div>{formatBalance(token.balance)}</div>
                          <div className="text-xs text-muted-foreground">{formatUsd(token.usdValue)}</div>
                        </div>
                      </div>
                      <div className="flex gap-1 mt-2">
                        <Button variant="outline" size="sm" className="h-7 text-xs w-full gap-1">
                          <ArrowRightLeft className="h-3 w-3" />
                          Swap
                        </Button>
                        <Button variant="outline" size="sm" className="h-7 text-xs w-full gap-1">
                          <Plus className="h-3 w-3" />
                          Add
                        </Button>
                      </div>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}