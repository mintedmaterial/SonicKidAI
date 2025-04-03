import { Avatar } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";
import { ChatMessage } from "@shared/schema";

interface ChatMessageProps {
  message: ChatMessage;
  className?: string;
}

export function ChatMessageComponent({ message, className }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn(
      "flex w-full gap-2 p-4",
      isUser ? "flex-row-reverse" : "flex-row",
      className
    )}>
      <Avatar>
        <div className={cn(
          "w-8 h-8 rounded-full flex items-center justify-center",
          isUser ? "bg-primary" : "bg-secondary"
        )}>
          {isUser ? "U" : 
            message.agentType === "anthropic" ? "A" : 
            message.agentType === "instructor" ? "I" : 
            "T"}
        </div>
      </Avatar>
      <div className={cn(
        "flex-1 rounded-lg p-3",
        isUser ? "bg-primary/10" : "bg-secondary/10"
      )}>
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
      </div>
    </div>
  );
}