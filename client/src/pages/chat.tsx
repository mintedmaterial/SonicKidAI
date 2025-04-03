import { Card } from "@/components/ui/card";
import { ChatBox } from "@/components/chat/ChatBox";

export default function ChatPage() {
  return (
    <div className="min-h-screen bg-black bg-gradient-to-b from-black to-background">
      <div className="absolute inset-0 bg-[url('/market_visualization_1740761270.png')] bg-no-repeat bg-center bg-contain opacity-10 pointer-events-none"></div>
      <div className="container mx-auto p-4 relative z-10">
        <h1 className="text-2xl font-bold mb-4">
          <span className="text-pink-500">SonicKid</span> <span className="text-primary">AI</span> Chat Interface
        </h1>
        <Card className="min-h-[600px] flex flex-col bg-background/80 backdrop-blur border border-primary/20 shadow-lg">
          <ChatBox />
        </Card>
      </div>
    </div>
  );
}
