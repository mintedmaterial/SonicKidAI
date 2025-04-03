import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-black bg-gradient-to-b from-black to-background">
      <div className="absolute inset-0 bg-[url('/market_visualization_1740761270.png')] bg-no-repeat bg-center bg-contain opacity-10 pointer-events-none"></div>
      <Card className="w-full max-w-md mx-4 relative z-10 bg-background/80 backdrop-blur border border-primary/20 shadow-lg">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center mb-4 text-center">
            <AlertCircle className="h-12 w-12 text-pink-500 mb-2" />
            <h1 className="text-2xl font-bold">
              <span className="text-pink-500">404</span> Page Not Found
            </h1>
          </div>

          <p className="mt-4 text-sm text-muted-foreground text-center">
            The page you're looking for doesn't exist in the SonicKid AI network.
          </p>
          
          <div className="flex justify-center mt-6">
            <a href="/" className="py-2 px-4 bg-primary hover:bg-primary/90 text-white rounded-md transition-colors">
              Return Home
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
