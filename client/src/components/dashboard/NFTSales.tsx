import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Avatar } from "@/components/ui/avatar";
import { Paintbrush, ImageIcon, RefreshCw } from "lucide-react";

// Interface for PaintSwap NFT sales from API
interface NFTSale {
  id: string;
  address: string; // NFT contract address
  tokenId: string;
  price: string;
  priceUsd?: string;
  tokenName?: string;
  collection?: {
    name: string;
    address: string;
    image?: string;
  };
  buyer?: {
    address: string;
  };
  maxBidder?: string; // Alternative to buyer for auction
  seller?: {
    address: string;
  };
  maxBid?: string; // Alternative price for auctions
  transactionHash?: string; 
  startTime?: string; // Alternative to timestamp
  timestamp?: string;
  sold?: boolean;
  isAuction?: boolean;
  nft?: {
    name?: string;
    image?: string;
    tokenURI?: string;
    description?: string;
    attributes?: any[];
  };
}

interface NFTSalesProps {
  className?: string;
}

export function NFTSales({ className }: NFTSalesProps) {
  const [mounted, setMounted] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  
  useEffect(() => {
    setMounted(true);
  }, []);

  // Get time since last update for display
  const getTimeSinceUpdate = () => {
    const now = new Date();
    const diffMs = now.getTime() - lastUpdated.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'just now';
    if (diffMins === 1) return '1 min ago';
    return `${diffMins} mins ago`;
  };

  // Query for PaintSwap NFT sales
  const { data: salesData, isLoading, error, refetch, isFetching } = useQuery<{ success: boolean; data: NFTSale[] }>({
    queryKey: ['/api/nft/sales'],
    refetchInterval: 300000, // Refresh every 5 minutes
    enabled: mounted
  });
  
  // Update the last updated time when data is fetched
  useEffect(() => {
    if (salesData) {
      setLastUpdated(new Date());
    }
  }, [salesData]);

  // Handle manual refresh
  const handleRefresh = () => {
    refetch();
  };

  // Format time from timestamp
  const formatTime = (timestamp: string | number) => {
    try {
      // Handle Unix timestamps (seconds since epoch)
      const date = typeof timestamp === 'string' && !timestamp.includes('-') && !timestamp.includes(':') && timestamp.length <= 10
        ? new Date(parseInt(timestamp) * 1000)  // Convert seconds to milliseconds
        : new Date(timestamp);
      
      return new Intl.DateTimeFormat('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      }).format(date);
    } catch (e) {
      return 'Unknown time';
    }
  };

  // Format price for display
  const formatPrice = (price: string) => {
    try {
      // If price is a large number (likely in wei), convert to ETH
      if (price && price.length > 10) {
        const weiValue = BigInt(price);
        const ethValue = Number(weiValue) / 1e18;
        
        if (ethValue >= 1000000) {
          return `${(ethValue / 1000000).toFixed(2)}M`;
        } else if (ethValue >= 1000) {
          return `${(ethValue / 1000).toFixed(2)}K`;
        } else {
          return ethValue.toFixed(2);
        }
      } else {
        // Regular price formatting
        const numPrice = parseFloat(price);
        if (numPrice >= 1000000) {
          return `${(numPrice / 1000000).toFixed(2)}M`;
        } else if (numPrice >= 1000) {
          return `${(numPrice / 1000).toFixed(2)}K`;
        } else {
          return numPrice.toFixed(2);
        }
      }
    } catch (e) {
      return price || '0';
    }
  };

  // Truncate address for display
  const truncateAddress = (address: string) => {
    if (!address) return 'Unknown';
    return `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
  };

  // Open collection on PaintSwap
  const openCollection = (collection: NFTSale['collection']) => {
    if (!collection) return;
    
    // Open the collection on PaintSwap
    window.open(`https://paintswap.finance/marketplace/${collection.address}`, '_blank');
  };

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex justify-between items-center">
          <CardTitle className="text-lg flex items-center">
            <Paintbrush className="h-5 w-5 mr-2 text-pink-500" />
            Recent NFT Sales
          </CardTitle>
          <div className="flex items-center text-xs text-muted-foreground">
            <span className="mr-2">Updated {getTimeSinceUpdate()}</span>
            <button 
              onClick={handleRefresh} 
              disabled={isFetching}
              className="p-1 rounded-full hover:bg-muted transition-colors disabled:opacity-50"
              title="Refresh sales data"
            >
              <RefreshCw 
                className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} 
              />
            </button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex justify-center items-center h-64 text-muted-foreground">
            Loading NFT sales data...
          </div>
        ) : error ? (
          <div className="flex justify-center items-center h-64 text-muted-foreground">
            Unable to load NFT sales at this time.
          </div>
        ) : !salesData || !salesData.data || salesData.data.length === 0 ? (
          <div className="flex justify-center items-center h-64 text-muted-foreground">
            No recent NFT sales found.
          </div>
        ) : (
          <ScrollArea className="h-[400px] pr-4">
            <div className="space-y-4">
              {salesData.data.map((sale) => {
                // Handle different formats from PaintSwap API
                const effectivePrice = (sale.maxBid && sale.maxBid !== "0") ? sale.maxBid : (sale.price || "0");
                const buyerAddress = sale.buyer?.address || sale.maxBidder || "";
                const sellerAddress = sale.seller?.address || "";
                const timestamp = sale.timestamp || sale.startTime || "";
                const isListing = !sale.sold && (!sale.buyer || !buyerAddress);
                
                return (
                  <div 
                    key={sale.id} 
                    className="flex items-start space-x-4 p-3 rounded-lg bg-card/50 hover:bg-card/80 transition-colors border border-border/50"
                    onClick={() => window.open(`https://paintswap.finance/marketplace/assets/${sale.address}/${sale.tokenId}`, '_blank')}
                    style={{ cursor: 'pointer' }}
                  >
                    <Avatar className="h-12 w-12 rounded-md overflow-hidden">
                      {sale.nft && sale.nft.image ? (
                        <img 
                          src={sale.nft.image} 
                          alt={sale.nft?.name || `NFT #${sale.tokenId}`}
                          className="h-full w-full object-cover"
                          onError={(e) => {
                            // Fallback to default icon if image fails to load
                            e.currentTarget.style.display = 'none';
                            e.currentTarget.parentElement!.querySelector('div')!.style.display = 'flex';
                          }}
                        />
                      ) : (
                        <div className="flex items-center justify-center h-full w-full bg-primary/10">
                          <ImageIcon className="h-5 w-5 text-primary" />
                        </div>
                      )}
                    </Avatar>
                    <div className="flex-1 space-y-1 overflow-hidden">
                      <div className="flex justify-between items-start">
                        <p className="font-medium truncate">
                          {sale.nft?.name || sale.tokenName || `NFT #${sale.tokenId}`}
                        </p>
                        <Badge variant="secondary" className="ml-2 whitespace-nowrap">
                          {`${formatPrice(effectivePrice)} Sonic`}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">
                        {sale.address ? truncateAddress(sale.address) : 'Unknown'} • {timestamp ? formatTime(timestamp) : 'Recently'}
                      </p>
                      <div className="flex justify-between text-xs text-muted-foreground">
                        {isListing ? (
                          <span className="truncate font-medium text-green-500">
                            Listed for Sale
                          </span>
                        ) : (
                          <>
                            <span className="truncate">
                              From: {truncateAddress(sellerAddress)}
                            </span>
                            <span className="truncate ml-2">
                              To: {truncateAddress(buyerAddress)}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}