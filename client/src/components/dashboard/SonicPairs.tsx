import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';

export interface TokenInfo {
  address: string;
  name: string;
  symbol: string;
}

export interface PairData {
  pairAddress: string;
  baseToken: TokenInfo;
  quoteToken: TokenInfo;
  liquidity: number;
  volume24h: number;
  priceUsd: number;
  priceChange24h: number;
  txns24h: {
    buys: number;
    sells: number;
  };
  dexId: string;
  chainId?: string;
}

interface SonicPairsProps {
  pairsData?: PairData[];
  isLoading?: boolean;
  error?: Error | null;
}

export default function SonicPairs({ pairsData, isLoading = false, error = null }: SonicPairsProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Format currency with appropriate suffix (K, M, B)
  const formatCurrency = (value: number) => {
    if (value >= 1_000_000_000) {
      return `$${(value / 1_000_000_000).toFixed(2)}B`;
    } else if (value >= 1_000_000) {
      return `$${(value / 1_000_000).toFixed(2)}M`;
    } else if (value >= 1_000) {
      return `$${(value / 1_000).toFixed(2)}K`;
    } else {
      return `$${value.toFixed(2)}`;
    }
  };

  // Truncate long addresses
  const truncateAddress = (address: string) => {
    if (!address) return "";
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle className="text-xl">Top Sonic Pairs</CardTitle>
          <Badge className="bg-purple-500 hover:bg-purple-600 cursor-default" variant="secondary">
            {pairsData && pairsData.length > 0 ? `${pairsData.length} Pairs` : 'Loading...'}
          </Badge>
        </div>
        <CardDescription>
          Top trading pairs on Sonic chain by liquidity
        </CardDescription>
      </CardHeader>
      <CardContent className="flex-grow p-0">
        {isLoading ? (
          <div className="p-4 text-center">Loading pairs data...</div>
        ) : error ? (
          <div className="p-4 text-center text-red-500">Error loading pairs: {error.message}</div>
        ) : pairsData && pairsData.length > 0 ? (
          <ScrollArea className="h-[350px]">
            <div className="p-4">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-sm font-medium text-gray-500">
                    <th className="pb-2">Pair</th>
                    <th className="pb-2 text-right">Price</th>
                    <th className="pb-2 text-right">24h</th>
                    <th className="pb-2 text-right">Liquidity</th>
                  </tr>
                </thead>
                <tbody>
                  {pairsData.map((pair) => (
                    <tr key={pair.pairAddress} className="border-t border-gray-100">
                      <td className="py-3">
                        <div className="font-medium">
                          {pair.baseToken.symbol}/{pair.quoteToken.symbol}
                        </div>
                        <div className="text-xs text-gray-500">{pair.dexId}</div>
                      </td>
                      <td className="py-3 text-right">
                        ${pair.priceUsd.toFixed(4)}
                      </td>
                      <td className={`py-3 text-right ${pair.priceChange24h > 0 ? 'text-green-500' : pair.priceChange24h < 0 ? 'text-red-500' : 'text-gray-500'}`}>
                        {pair.priceChange24h > 0 ? '+' : ''}{pair.priceChange24h.toFixed(2)}%
                      </td>
                      <td className="py-3 text-right">
                        {formatCurrency(pair.liquidity)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ScrollArea>
        ) : (
          <div className="p-4 text-center">No pairs data available</div>
        )}
      </CardContent>
    </Card>
  );
}