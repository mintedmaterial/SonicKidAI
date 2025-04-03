import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-black bg-gradient-to-b from-black to-background">
      <div className="absolute inset-0 bg-[url('/market_visualization_1740761270.png')] bg-no-repeat bg-center bg-contain opacity-15 pointer-events-none"></div>
      <Card className="w-full max-w-md mx-4 relative z-10 bg-background/80 backdrop-blur border border-primary/20 shadow-lg">
        <CardHeader className="pb-2">
          <CardTitle className="text-center text-2xl">
            <span className="text-pink-500">SonicKid</span> <span className="text-primary">AI</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-center mb-4">
            Advanced cross-blockchain trading with AI-driven market intelligence and multi-platform integration.
          </p>
          <div className="flex justify-center gap-4 mt-4">
            <a href="/dashboard" className="py-2 px-4 bg-pink-500 hover:bg-pink-600 text-white rounded-md transition-colors">
              Dashboard
            </a>
            <a href="/enhanced-dashboard" className="py-2 px-4 bg-primary hover:bg-primary/90 text-white rounded-md transition-colors">
              Enhanced View
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
