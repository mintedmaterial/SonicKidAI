import { Card } from "@/components/ui/card";
import { useQuery } from "@tanstack/react-query";
import { Activity } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

interface FearGreedChartProps {
  width?: string;
  height?: string;
  className?: string;
}

interface FearGreedData {
  value: number;
  value_classification: string;
  timestamp: string;
  time_until_update: string;
}

interface FearGreedResponse {
  data: FearGreedData[];
}

export function FearGreedChart({ width = "100%", height = "300px", className = "" }: FearGreedChartProps) {
  const { data: fearGreedData, isLoading } = useQuery<FearGreedResponse>({
    queryKey: ['/api/market/fear-greed'],
    refetchInterval: 60000 * 10, // Refresh every 10 minutes
  });

  const currentValue = fearGreedData?.data?.[0]?.value;
  const classification = fearGreedData?.data?.[0]?.value_classification;

  const getValueColor = (value?: number) => {
    if (!value) return "text-gray-500";
    if (value <= 20) return "text-red-500";
    if (value <= 40) return "text-orange-500";
    if (value <= 60) return "text-yellow-500";
    if (value <= 80) return "text-lime-500";
    return "text-green-500";
  };

  return (
    <Card className={`p-4 bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5 ${className}`}>
      <h3 className="text-lg font-semibold flex items-center gap-2 mb-4">
        <Activity className="h-5 w-5 text-primary" />
        Fear & Greed Index
      </h3>
      
      {isLoading ? (
        <div className="flex flex-col items-center justify-center space-y-4">
          <Skeleton className="h-[200px] w-[200px] rounded-full" />
          <Skeleton className="h-4 w-32" />
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center">
          <div className="mb-4 relative">
            <img 
              src="https://alternative.me/crypto/fear-and-greed-index.png" 
              alt="Fear and Greed Index" 
              className="h-auto w-full max-w-[400px]"
              loading="lazy"
            />
          </div>
          
          {currentValue && (
            <div className="text-center mb-2">
              <span className="text-sm">Current value: </span>
              <span className={`text-xl font-bold ${getValueColor(currentValue)}`}>
                {currentValue} - {classification}
              </span>
            </div>
          )}
          
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Data from <a href="https://alternative.me/" target="_blank" rel="noopener noreferrer" className="underline hover:text-primary">Alternative.me</a>
          </p>
        </div>
      )}
    </Card>
  );
}