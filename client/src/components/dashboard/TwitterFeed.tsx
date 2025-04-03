import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Twitter, AlertCircle, Repeat, Heart, MessageCircle, Search, Tag, Bot, AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/hooks/use-toast";

interface Tweet {
  id: string;
  text: string;
  author: {
    username: string;
    profile_image_url?: string;
    name: string;
  };
  created_at: string;
  public_metrics?: {
    retweet_count: number;
    like_count: number;
    reply_count: number;
  };
}

export function TwitterFeed() {
  const [tweets, setTweets] = useState<Tweet[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [searchBy, setSearchBy] = useState<"creator" | "tweetId">("creator");
  const [searchActive, setSearchActive] = useState(false);
  const [testTweetText, setTestTweetText] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  // Define analysis result type with all the fields returned from the API
  const [analysisResult, setAnalysisResult] = useState<{
    success: boolean;
    shouldTag: boolean;
    tweet?: any;
    analysis?: {
      detectedKeywords: {
        critical: string[];
        marketEvents: string[];
        monitoredAssets: string[];
      };
      discordChannel: string;
      usingAI: boolean;
    };
  } | null>(null);

  const fetchTweets = async (params?: Record<string, string>) => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Build the URL with search parameters if provided
      let url = "/api/social/tweets";
      if (params) {
        const queryParams = new URLSearchParams();
        Object.entries(params).forEach(([key, value]) => {
          if (value) queryParams.append(key, value);
        });
        const queryString = queryParams.toString();
        if (queryString) {
          url += `?${queryString}`;
        }
      }
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`Error fetching tweets: ${response.status}`);
      }
      
      const data = await response.json();
      setTweets(data.tweets || []);
    } catch (e) {
      console.error("Error fetching tweets:", e);
      setError("Unable to load tweets. Please try again later.");
    } finally {
      setIsLoading(false);
    }
  };

  // Handle search submission
  const handleSearch = () => {
    if (!searchTerm) {
      // If search term is empty, reset to fetch all tweets
      setSearchActive(false);
      fetchTweets();
      return;
    }
    
    setSearchActive(true);
    
    // Create search params based on search type
    const params: Record<string, string> = {};
    if (searchBy === "creator") {
      params.creator = searchTerm;
    } else if (searchBy === "tweetId") {
      params.tweetId = searchTerm;
    }
    
    fetchTweets(params);
  };

  // Handle search reset
  const handleReset = () => {
    setSearchTerm("");
    setSearchBy("creator");
    setSearchActive(false);
    fetchTweets();
  };
  
  useEffect(() => {
    // Initial fetch of all tweets
    fetchTweets();
    
    // Set up polling for updates when not in search mode
    const interval = setInterval(() => {
      if (!searchActive) {
        fetchTweets();
      }
    }, 30 * 1000);
    
    return () => clearInterval(interval);
  }, [searchActive]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  // Extract hashtags and mentions from tweet text
  const formatTweetText = (text: string) => {
    // Replace hashtags with styled spans
    let formattedText = text.replace(/#(\w+)/g, '<span class="text-primary font-medium">#$1</span>');
    
    // Replace mentions with styled spans
    formattedText = formattedText.replace(/@(\w+)/g, '<span class="text-primary font-medium">@$1</span>');
    
    // Replace URLs with linked elements
    formattedText = formattedText.replace(
      /(https?:\/\/[^\s]+)/g, 
      '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-primary underline hover:text-primary/80">$1</a>'
    );
    
    return formattedText;
  };

  if (isLoading) {
    return (
      <Card className="bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Twitter className="h-5 w-5 text-primary" />
            Twitter Feed
          </CardTitle>
          <CardDescription>Latest tweets from crypto influencers</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="flex gap-3 animate-pulse">
                <div className="rounded-full bg-muted h-10 w-10 flex-shrink-0"></div>
                <div className="w-full">
                  <div className="h-4 bg-muted rounded w-1/3 mb-2"></div>
                  <div className="h-3 bg-muted rounded w-full mb-1"></div>
                  <div className="h-3 bg-muted rounded w-4/5"></div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center gap-2">
            <Twitter className="h-5 w-5 text-primary" />
            Twitter Feed
          </CardTitle>
          <CardDescription>Latest tweets from crypto influencers</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <AlertCircle className="h-12 w-12 mx-auto mb-2 opacity-20" />
            <p>{error}</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
      <CardHeader className="pb-2">
        <CardTitle className="text-lg flex items-center gap-2">
          <Twitter className="h-5 w-5 text-primary" />
          Twitter Feed
        </CardTitle>
        <CardDescription>Latest tweets from crypto influencers</CardDescription>
      </CardHeader>
      <CardContent>
        {/* Search bar */}
        <div className="flex gap-2 mb-4">
          <div className="flex-1">
            <Input
              type="text"
              placeholder={searchBy === "creator" ? "Search by creator name..." : "Search by tweet ID..."}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSearch();
              }}
              className="w-full"
            />
          </div>
          <div className="flex gap-1">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={() => {
                setSearchBy(searchBy === "creator" ? "tweetId" : "creator");
              }}
              className="whitespace-nowrap"
            >
              {searchBy === "creator" ? "By Creator" : "By Tweet ID"}
            </Button>
            <Button 
              variant="default" 
              size="sm" 
              onClick={handleSearch}
              className="px-3"
            >
              <Search className="h-4 w-4" />
            </Button>
            {searchActive && (
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleReset}
                className="px-3"
              >
                Clear
              </Button>
            )}
          </div>
        </div>
        
        {searchActive && (
          <div className="mb-3 text-sm">
            <Badge variant="outline">
              Searching {searchBy === "creator" ? "creators" : "tweet IDs"}: {searchTerm}
            </Badge>
          </div>
        )}
        
        <ScrollArea className="h-[350px] pr-4">
          {tweets.length > 0 ? (
            <div className="space-y-4">
              {tweets.map((tweet) => (
                <div key={tweet.id} className="border border-primary/10 rounded-lg p-4 bg-background/70 hover:bg-background/80 transition-colors">
                  <div className="flex items-start gap-3">
                    <Avatar className="h-10 w-10 border border-primary/20">
                      <AvatarImage src={tweet.author.profile_image_url} alt={tweet.author.username} />
                      <AvatarFallback className="bg-primary/10 text-primary">
                        {tweet.author.name.substring(0, 2)}
                      </AvatarFallback>
                    </Avatar>
                    
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <div>
                          <span className="font-medium">{tweet.author.name}</span>
                          <span className="text-muted-foreground ml-1 text-sm">@{tweet.author.username}</span>
                        </div>
                        <Badge variant="outline" className="text-xs">
                          Twitter
                        </Badge>
                      </div>
                      
                      <div 
                        className="mb-2 text-sm"
                        dangerouslySetInnerHTML={{ __html: formatTweetText(tweet.text) }}
                      />
                      
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>{formatDate(tweet.created_at)}</span>
                        
                        {tweet.public_metrics && (
                          <div className="flex items-center gap-3">
                            <div className="flex items-center gap-1">
                              <MessageCircle className="h-3 w-3" />
                              <span>{tweet.public_metrics.reply_count}</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <Repeat className="h-3 w-3" />
                              <span>{tweet.public_metrics.retweet_count}</span>
                            </div>
                            <div className="flex items-center gap-1">
                              <Heart className="h-3 w-3" />
                              <span>{tweet.public_metrics.like_count}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <p>No tweets available</p>
            </div>
          )}
        </ScrollArea>

        {/* Agent Tagging Testing Tool */}
        <div className="mt-3 pt-3 border-t border-primary/10">
          <div className="flex justify-between items-center">
            <div className="text-sm text-muted-foreground">Test Agent Tagging System</div>
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="outline" size="sm" className="gap-1">
                  <Tag className="h-4 w-4" />
                  Test Tagging
                </Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[550px]">
                <DialogHeader>
                  <DialogTitle>Test Agent Tagging System</DialogTitle>
                  <DialogDescription>
                    Enter a tweet to analyze whether it should tag the agent for immediate attention.
                  </DialogDescription>
                </DialogHeader>
                
                <div className="grid gap-4 py-4">
                  <div className="grid gap-2">
                    <label htmlFor="tweet-text" className="text-sm font-medium">Tweet Content</label>
                    <Textarea
                      id="tweet-text"
                      value={testTweetText}
                      onChange={(e) => setTestTweetText(e.target.value)}
                      rows={5}
                      placeholder="Enter tweet text here... e.g. 'BREAKING: Ethereum merge date announced for September 15th! $ETH price surging on the news.'"
                    />
                  </div>
                  
                  {analysisResult && (
                    <div className={`p-4 rounded-lg border ${analysisResult.shouldTag ? 'bg-green-50 border-green-200 dark:bg-green-900/20 dark:border-green-900' : 'bg-muted border-muted-foreground/20'}`}>
                      <div className="flex items-center gap-2 mb-2">
                        {analysisResult.shouldTag ? (
                          <>
                            <Bot className="h-5 w-5 text-green-600 dark:text-green-400" />
                            <span className="font-medium">Agent would be tagged! 🚨</span>
                          </>
                        ) : (
                          <>
                            <AlertTriangle className="h-5 w-5 text-muted-foreground" />
                            <span className="font-medium">Agent would NOT be tagged</span>
                          </>
                        )}
                      </div>
                      
                      <div className="text-sm space-y-3">
                        {analysisResult.tweet && (
                          <p className="text-muted-foreground">
                            Tweet ID: {analysisResult.tweet.id}
                          </p>
                        )}
                        
                        {/* Display detected keywords */}
                        {analysisResult.analysis && (
                          <div className="pt-2 border-t border-border/50">
                            <h5 className="text-sm font-medium mb-2">Decision Factors:</h5>
                            <div className="space-y-2">
                              {/* Critical keywords */}
                              {analysisResult.analysis.detectedKeywords.critical.length > 0 && (
                                <div>
                                  <p className="text-xs font-medium text-red-500">Security/Critical Keywords:</p>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {analysisResult.analysis.detectedKeywords.critical.map((keyword, idx) => (
                                      <Badge key={idx} variant="destructive" className="text-xs">{keyword}</Badge>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                              {/* Market event keywords */}
                              {analysisResult.analysis.detectedKeywords.marketEvents.length > 0 && (
                                <div>
                                  <p className="text-xs font-medium text-blue-500">Market Event Keywords:</p>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {analysisResult.analysis.detectedKeywords.marketEvents.map((keyword, idx) => (
                                      <Badge key={idx} variant="default" className="text-xs bg-blue-500">{keyword}</Badge>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                              {/* Monitored assets */}
                              {analysisResult.analysis.detectedKeywords.monitoredAssets.length > 0 && (
                                <div>
                                  <p className="text-xs font-medium text-purple-500">Monitored Assets:</p>
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {analysisResult.analysis.detectedKeywords.monitoredAssets.map((asset, idx) => (
                                      <Badge key={idx} variant="outline" className="text-xs border-purple-500">{asset}</Badge>
                                    ))}
                                  </div>
                                </div>
                              )}
                              
                              {/* No keywords detected */}
                              {analysisResult.analysis.detectedKeywords.critical.length === 0 && 
                               analysisResult.analysis.detectedKeywords.marketEvents.length === 0 && 
                               analysisResult.analysis.detectedKeywords.monitoredAssets.length === 0 && (
                                <p className="text-xs text-muted-foreground">No specific keywords detected. Analysis performed using AI.</p>
                              )}
                              
                              {/* Discord notification info */}
                              {analysisResult.shouldTag && (
                                <div className="mt-3 pt-2 border-t border-border/50 text-xs text-muted-foreground">
                                  <p>
                                    Notification would be sent to Discord channel ID: {analysisResult.analysis.discordChannel}
                                  </p>
                                  <p className="mt-1">
                                    {analysisResult.analysis.usingAI 
                                      ? "Analysis includes AI-based content evaluation via Anthropic Claude model."
                                      : "Analysis based on keyword matching only (AI model not available)."}
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
                
                <DialogFooter>
                  <Button 
                    variant="default" 
                    onClick={analyzeTweetForTagging}
                    disabled={isAnalyzing || !testTweetText.trim()}
                  >
                    {isAnalyzing ? 'Analyzing...' : 'Analyze Tweet'}
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  // Function to analyze tweet for agent tagging
  async function analyzeTweetForTagging() {
    if (!testTweetText.trim()) return;
    
    console.log("Starting tweet analysis:", testTweetText.substring(0, 50) + "...");
    setIsAnalyzing(true);
    setAnalysisResult(null);
    
    try {
      // Send request to analyze the tweet
      console.log("Sending request to /api/social/analyze-tweet endpoint");
      const response = await fetch('/api/social/analyze-tweet', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          tweetText: testTweetText,
          tweetId: `test-${Date.now()}`, // Generate a test ID
        }),
      });
      
      console.log("Response status:", response.status);
      
      if (!response.ok) {
        throw new Error(`Error analyzing tweet: ${response.status}`);
      }
      
      // Parse the response
      const data = await response.json();
      console.log("Analysis result:", data);
      setAnalysisResult(data);
      
      // Show toast notification
      toast({
        title: data.shouldTag 
          ? "Agent would be tagged! 🚨" 
          : "Agent would NOT be tagged ✓",
        description: data.shouldTag 
          ? "This tweet contains content that would trigger agent notification in Discord channel #1333615004305330348." 
          : "This tweet does not meet the criteria for agent notification.",
        variant: data.shouldTag ? "default" : undefined,
      });
      
      // Log the decision details
      if (data.shouldTag) {
        console.log("🔔 Tweet would trigger agent tagging in Discord!");
        console.log("Tweet content:", testTweetText);
        console.log("Discord channel: #1333615004305330348");
      } else {
        console.log("Tweet did not meet tagging criteria.");
      }
      
    } catch (error) {
      console.error('Error analyzing tweet:', error);
      toast({
        title: "Analysis Failed",
        description: "There was a problem analyzing the tweet. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsAnalyzing(false);
    }
  }
}