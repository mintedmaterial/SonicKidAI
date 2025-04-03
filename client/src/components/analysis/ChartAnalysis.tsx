import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { FileUploader } from '@/components/ui/file-uploader';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Loader2, Trash2, Image as ImageIcon, BarChart2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

interface UploadedFile {
  filename: string;
  path: string;
  created: string;
  size: number;
}

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface ApiResponse {
  success: boolean;
  data: UploadedFile[];
}

export default function ChartAnalysis() {
  const [selectedImage, setSelectedImage] = useState<UploadedFile | null>(null);
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  
  const { toast } = useToast();

  // Query to get all uploaded images
  const { 
    data: apiResponse, 
    isLoading: isLoadingImages, 
    refetch: refetchImages 
  } = useQuery<ApiResponse>({ 
    queryKey: ['/api/uploads/images'],
    refetchOnWindowFocus: false
  });
  
  // Safely extract the images array
  const images = apiResponse?.data || [];

  // Handle successful upload
  const handleUploadSuccess = (fileData: any) => {
    refetchImages();
    setSelectedImage({
      filename: fileData.filename,
      path: fileData.path,
      created: new Date().toISOString(),
      size: fileData.size
    });
    
    // Add a welcome message when a new image is uploaded
    setMessages([{
      role: 'assistant',
      content: 'I can analyze this chart for you. What would you like to know about it?'
    }]);
  };

  // Handle image selection
  const handleSelectImage = (image: UploadedFile) => {
    setSelectedImage(image);
    setMessages([{
      role: 'assistant',
      content: 'I can analyze this chart for you. What would you like to know about it?'
    }]);
  };

  // Handle prompt submission
  const handleSubmit = async () => {
    if (!prompt.trim() || !selectedImage) return;
    
    // Add user message
    const userMessage: ChatMessage = {
      role: 'user',
      content: prompt
    };
    
    setMessages([...messages, userMessage]);
    setIsLoading(true);
    
    try {
      // Call the instructor agent with the image context
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: prompt,
          mode: 'instructor',
          source: 'chart-analysis', // Add the source parameter to differentiate from regular chat
          context: {
            imageUrl: selectedImage.path,
            analysisType: 'chart',
            chartType: 'crypto'
          }
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to get analysis');
      }
      
      const data = await response.json();
      
      // Add assistant message
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: data.data?.message || 'I could not analyze this chart properly. Please try a different approach.'
      };
      
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Analysis failed',
        description: error instanceof Error ? error.message : 'Failed to analyze the chart'
      });
    } finally {
      setIsLoading(false);
      setPrompt('');
    }
  };

  return (
    <div className="w-full space-y-6">
      <h1 className="text-2xl font-bold">Chart Analysis</h1>
      <p className="text-muted-foreground">Upload and analyze cryptocurrency charts with AI</p>
      
      <Tabs defaultValue="upload" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="upload">
            <ImageIcon className="mr-2 h-4 w-4" />
            Upload
          </TabsTrigger>
          <TabsTrigger value="analyze">
            <BarChart2 className="mr-2 h-4 w-4" />
            Analyze
          </TabsTrigger>
        </TabsList>
        
        {/* Upload Tab */}
        <TabsContent value="upload" className="space-y-4">
          <FileUploader 
            title="Upload Chart Image"
            description="Upload a screenshot or image of a cryptocurrency chart to analyze"
            accept="image/*"
            onSuccess={handleUploadSuccess}
          />
          
          <div className="space-y-4 mt-6">
            <h3 className="text-lg font-medium">Previously Uploaded Images</h3>
            
            {isLoadingImages ? (
              <div className="flex justify-center items-center p-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
              </div>
            ) : images.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {images.map((image: UploadedFile) => (
                  <Card 
                    key={image.filename} 
                    className={`overflow-hidden cursor-pointer transition-all ${
                      selectedImage?.filename === image.filename 
                        ? 'ring-2 ring-primary' 
                        : 'hover:ring-1 hover:ring-primary/50'
                    }`}
                    onClick={() => handleSelectImage(image)}
                  >
                    <div className="aspect-video relative overflow-hidden">
                      <img 
                        src={image.path} 
                        alt={image.filename} 
                        className="object-cover w-full h-full"
                      />
                    </div>
                    <CardFooter className="p-2 text-xs text-muted-foreground justify-between">
                      <span>{new Date(image.created).toLocaleDateString()}</span>
                      <span>{Math.round(image.size / 1024)} KB</span>
                    </CardFooter>
                  </Card>
                ))}
              </div>
            ) : (
              <div className="text-center p-8 border border-dashed rounded-lg">
                <p className="text-muted-foreground">No images uploaded yet</p>
              </div>
            )}
          </div>
        </TabsContent>
        
        {/* Analysis Tab */}
        <TabsContent value="analyze" className="space-y-4">
          {selectedImage ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <Card>
                  <CardHeader>
                    <CardTitle>Selected Chart Image</CardTitle>
                    <CardDescription>
                      This chart will be analyzed by our AI
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-0">
                    <div className="aspect-video w-full overflow-hidden">
                      <img 
                        src={selectedImage.path} 
                        alt="Selected chart" 
                        className="object-contain w-full h-full"
                      />
                    </div>
                  </CardContent>
                  <CardFooter className="justify-between">
                    <div className="text-sm text-muted-foreground">
                      Uploaded: {new Date(selectedImage.created).toLocaleString()}
                    </div>
                    <Button
                      variant="ghost" 
                      size="sm"
                      onClick={() => setSelectedImage(null)}
                    >
                      Change
                    </Button>
                  </CardFooter>
                </Card>
              </div>
              
              <div className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>AI Analysis</CardTitle>
                    <CardDescription>
                      Ask questions about the chart to analyze it
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="h-[300px] overflow-y-auto space-y-4 mb-4">
                      {messages.map((message, index) => (
                        <div 
                          key={index} 
                          className={`p-3 rounded-lg ${
                            message.role === 'user' 
                              ? 'bg-muted ml-12' 
                              : 'bg-primary/10 mr-12'
                          }`}
                        >
                          <p className="text-sm font-semibold mb-1">
                            {message.role === 'user' ? 'You' : 'AI Assistant'}
                          </p>
                          <div className="text-sm whitespace-pre-wrap">
                            {message.content}
                          </div>
                        </div>
                      ))}
                      {isLoading && (
                        <div className="flex justify-center py-4">
                          <Loader2 className="h-6 w-6 animate-spin text-primary" />
                        </div>
                      )}
                    </div>
                    
                    <div className="flex gap-2">
                      <Textarea
                        placeholder="Ask about the chart (e.g., 'What's the trend?', 'Identify support levels')"
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        className="flex-1"
                        disabled={isLoading}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSubmit();
                          }
                        }}
                      />
                      <Button 
                        onClick={handleSubmit} 
                        disabled={!prompt.trim() || isLoading}
                      >
                        {isLoading ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          'Send'
                        )}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
                
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle>Analysis Tips</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="text-sm space-y-1 list-disc list-inside text-muted-foreground">
                      <li>Ask about support and resistance levels</li>
                      <li>Identify chart patterns and trend directions</li>
                      <li>Request trading volume analysis</li>
                      <li>Ask for potential price targets</li>
                      <li>Get insights on market sentiment</li>
                    </ul>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
            <Card>
              <CardContent className="p-8 text-center">
                <ImageIcon className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                <h3 className="text-lg font-medium mb-2">No Chart Selected</h3>
                <p className="text-muted-foreground mb-4">
                  Please upload or select an existing chart image to analyze
                </p>
                <Button onClick={() => {
                  const element = document.querySelector('[data-value="upload"]');
                  if (element instanceof HTMLElement) {
                    element.click();
                  }
                }}>
                  Go to Upload
                </Button>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}