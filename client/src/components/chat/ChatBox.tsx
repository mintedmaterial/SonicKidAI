import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { ChatMessageComponent } from "./ChatMessage";
import { useToast } from "@/hooks/use-toast";
import { apiRequest } from "@/lib/queryClient";
import type { ChatMessage, InsertChatMessage } from "@shared/schema";

interface ChatResponse {
  success: boolean;
  data: ChatMessage[];
}

export function ChatBox() {
  const [message, setMessage] = useState("");
  const [agentType, setAgentType] = useState<"anthropic" | "instructor" | "tophat">("anthropic");
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery<ChatResponse>({
    queryKey: ["/api/chat/messages", "chat"],
    queryFn: async () => {
      const response = await fetch('/api/chat/messages?source=chat');
      if (!response.ok) {
        throw new Error('Failed to fetch chat messages');
      }
      return response.json();
    }
  });
  
  // Safely extract messages array from the response
  const messages = data?.data || [];

  const sendMessage = useMutation({
    mutationFn: async (content: string) => {
      try {
        const response = await fetch('/api/chat/message', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            message: content,
            mode: agentType === 'instructor' ? 'instructor' : 'standard',
            source: 'chat' // Specify this is from the chat interface
          })
        });
        
        if (!response.ok) {
          throw new Error('Failed to send message');
        }
        
        return response.json();
      } catch (error) {
        console.error('Error sending message:', error);
        throw error;
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/chat/messages", "chat"] });
      setMessage("");
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: "Failed to send message. Please try again.",
        variant: "destructive",
      });
      console.error("Chat error:", error);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;
    sendMessage.mutate(message);
  };

  return (
    <Card className="flex flex-col h-[600px] max-w-2xl mx-auto">
      <div className="p-4 border-b">
        <Select value={agentType} onValueChange={(value: "anthropic" | "instructor" | "tophat") => setAgentType(value)}>
          <SelectTrigger>
            <SelectValue placeholder="Select agent" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="anthropic">Anthropic Agent</SelectItem>
            <SelectItem value="instructor">Instructor Agent</SelectItem>
            <SelectItem value="tophat">TopHat Agent</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <ScrollArea className="flex-1 p-4">
        {messages.length > 0 ? (
          messages.map((msg: ChatMessage, index: number) => (
            <ChatMessageComponent 
              key={msg.id ? msg.id.toString() : `msg-${index}`} 
              message={msg} 
            />
          ))
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            No messages yet. Start a conversation!
          </div>
        )}
      </ScrollArea>

      <form onSubmit={handleSubmit} className="p-4 border-t flex gap-2">
        <Input
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Type your message..."
          disabled={sendMessage.isPending}
        />
        <Button type="submit" disabled={sendMessage.isPending}>
          Send
        </Button>
      </form>
    </Card>
  );
}