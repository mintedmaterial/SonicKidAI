import React from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  TrendingUp,
  TrendingDown,
  ExternalLink,
  DollarSign,
  Layers,
  Droplet,
  Star
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

// Define the interface for the project data
export interface ProjectOfWeek {
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

interface AdSpaceProps {
  projectData?: ProjectOfWeek;
  isLoading?: boolean;
}

export function AdSpace({ projectData, isLoading = false }: AdSpaceProps) {
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

  // Render loading state if data is loading
  if (isLoading) {
    return (
      <Card className="p-4 bg-background/30 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5 overflow-hidden">
        <div className="flex flex-col md:flex-row gap-6">
          <div className="md:w-1/3 w-full flex justify-center items-center">
            <Skeleton className="h-40 w-40 rounded-lg" />
          </div>
          <div className="md:w-2/3 w-full space-y-4">
            <div className="flex justify-between items-start">
              <div>
                <Skeleton className="h-7 w-48 mb-2" />
                <Skeleton className="h-5 w-24" />
              </div>
              <Skeleton className="h-8 w-24" />
            </div>
            <Skeleton className="h-16 w-full" />
            <div className="grid grid-cols-3 gap-2">
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
              <Skeleton className="h-12 w-full" />
            </div>
          </div>
        </div>
      </Card>
    );
  }

  // If no data, show a default placeholder
  if (!projectData) {
    return (
      <Card className="p-4 bg-background/30 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5 overflow-hidden">
        <div className="flex justify-center items-center h-40">
          <p className="text-muted-foreground text-center">
            Project of the week data not available at the moment.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4 bg-background/30 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5 overflow-hidden relative">
      {/* Sponsored badge */}
      <Badge variant="outline" className="absolute top-3 right-3 bg-background/50 backdrop-blur">
        <Star className="h-3 w-3 mr-1 text-yellow-500" /> Project of the Week
      </Badge>
      
      <div className="flex flex-col md:flex-row gap-6">
        {/* Project Logo */}
        <div className="md:w-1/3 w-full flex justify-center items-center">
          <div className="h-40 w-40 relative rounded-lg overflow-hidden border border-primary/20 bg-background/30 backdrop-blur">
            <img 
              src={projectData.artworkUrl} 
              alt={`${projectData.name} logo`}
              className="w-full h-full object-contain p-2"
            />
          </div>
        </div>
        
        {/* Project Information */}
        <div className="md:w-2/3 w-full">
          <div className="flex justify-between items-start mb-2">
            <div>
              <h2 className="text-xl font-bold">{projectData.name}</h2>
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{projectData.tokenSymbol}</Badge>
                <Badge variant="outline" className="capitalize">{projectData.chain}</Badge>
              </div>
            </div>
            {projectData.website && (
              <Button size="sm" variant="outline" asChild>
                <a href={projectData.website} target="_blank" rel="noopener noreferrer" className="flex items-center gap-1">
                  <span>Website</span>
                  <ExternalLink className="h-3 w-3" />
                </a>
              </Button>
            )}
          </div>
          
          <p className="text-muted-foreground mb-4 line-clamp-2">
            {projectData.description}
          </p>
          
          {/* Project Metrics */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Price */}
            <div className="bg-background/30 backdrop-blur rounded-lg p-3 border border-primary/10">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <DollarSign className="h-4 w-4" />
                <span>Price</span>
              </div>
              <div className="flex items-center justify-between">
                <p className="font-semibold">${projectData.price.toFixed(4)}</p>
                <div className={`flex items-center text-xs gap-1 ${
                  projectData.priceChange24h >= 0 ? 'text-green-500' : 'text-red-500'
                }`}>
                  {projectData.priceChange24h >= 0 ? 
                    <TrendingUp className="h-3 w-3" /> : 
                    <TrendingDown className="h-3 w-3" />
                  }
                  <span>{Math.abs(projectData.priceChange24h).toFixed(2)}%</span>
                </div>
              </div>
            </div>
            
            {/* Volume */}
            <div className="bg-background/30 backdrop-blur rounded-lg p-3 border border-primary/10">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <Layers className="h-4 w-4" />
                <span>24h Volume</span>
              </div>
              <p className="font-semibold">{formatCurrency(projectData.volume24h)}</p>
            </div>
            
            {/* Liquidity */}
            <div className="bg-background/30 backdrop-blur rounded-lg p-3 border border-primary/10">
              <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
                <Droplet className="h-4 w-4" />
                <span>Liquidity</span>
              </div>
              <p className="font-semibold">{formatCurrency(projectData.liquidity)}</p>
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}