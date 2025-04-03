import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  PieChart, 
  Pie, 
  Cell, 
  ResponsiveContainer, 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  Tooltip, 
  Legend 
} from "recharts";
import { 
  CheckCircle2, 
  XCircle, 
  AlertCircle, 
  Clock, 
  Activity, 
  LineChart,
  BarChart3,
  Bot,
  Server
} from "lucide-react";

// Define types for agent actions and stats
type AgentAction = {
  id: number;
  agentId: string;
  agentType: string;
  actionType: string;
  status: "success" | "failure" | "pending";
  errorMessage?: string;
  duration?: number;
  metadata?: Record<string, any>;
  createdAt: string;
};

type ActionsByType = {
  actionType: string;
  count: number;
  successRate: number;
};

type ActionsByAgentType = {
  agentType: string;
  count: number;
  successRate: number;
};

type AgentStats = {
  totalActions: number;
  successCount: number;
  failureCount: number;
  successRate: string;
  actionsByType: ActionsByType[];
  actionsByAgentType: ActionsByAgentType[];
  avgDuration: number;
};

export function AgentMonitoring() {
  const [mounted, setMounted] = useState(false);

  // Only run queries after component has mounted
  useEffect(() => {
    setMounted(true);
  }, []);

  // Fetch agent actions
  const { data: actions, isLoading: actionsLoading } = useQuery<AgentAction[]>({
    queryKey: ['/api/agent/actions'],
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: mounted,
  });

  // Fetch agent stats
  const { data: stats, isLoading: statsLoading } = useQuery<AgentStats>({
    queryKey: ['/api/agent/stats'],
    refetchInterval: 30000, // Refresh every 30 seconds
    enabled: mounted,
  });

  // Format date to a readable string
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  // Get icon for action status
  const getStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "failure":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  // Get color for action status
  const getStatusColor = (status: string) => {
    switch (status) {
      case "success":
        return "bg-green-500";
      case "failure":
        return "bg-red-500";
      case "pending":
        return "bg-yellow-500";
      default:
        return "bg-gray-500";
    }
  };

  // Loading state
  if (!mounted || actionsLoading || statsLoading) {
    return (
      <Card className="w-full bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            Agent Monitoring
          </CardTitle>
          <CardDescription>Loading agent activity data...</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  // Handle missing data
  if (!actions || !stats) {
    return (
      <Card className="w-full bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-primary" />
            Agent Monitoring
          </CardTitle>
          <CardDescription>No agent activity data available</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  // Data for success/failure pie chart
  const statusData = [
    { name: "Success", value: stats.successCount, color: "#22c55e" },
    { name: "Failure", value: stats.failureCount, color: "#ef4444" },
  ];

  // Data for agent types bar chart
  const agentTypeData = stats.actionsByAgentType.map((item) => ({
    name: item.agentType,
    count: item.count,
    successRate: parseFloat(item.successRate.toString()),
  }));

  // Data for action types bar chart
  const actionTypeData = stats.actionsByType.map((item) => ({
    name: item.actionType,
    count: item.count,
    successRate: parseFloat(item.successRate.toString()),
  }));

  return (
    <Card className="w-full bg-background/50 backdrop-blur border border-primary/20 shadow-lg shadow-primary/5">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Bot className="h-5 w-5 text-primary" />
          Agent Monitoring
        </CardTitle>
        <CardDescription>Monitor agent actions and their success rates</CardDescription>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="overview">
          <TabsList className="mb-4">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="actions">Action Log</TabsTrigger>
            <TabsTrigger value="analytics">Analytics</TabsTrigger>
          </TabsList>
          
          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Total Actions Card */}
              <Card className="p-4 bg-background/70 border border-primary/10">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Actions</p>
                    <p className="text-2xl font-bold">{stats.totalActions}</p>
                  </div>
                  <Activity className="h-8 w-8 text-primary opacity-70" />
                </div>
              </Card>
              
              {/* Success Rate Card */}
              <Card className="p-4 bg-background/70 border border-primary/10">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Success Rate</p>
                    <p className="text-2xl font-bold">{stats.successRate}%</p>
                  </div>
                  <CheckCircle2 className="h-8 w-8 text-green-500 opacity-70" />
                </div>
              </Card>
              
              {/* Average Duration Card */}
              <Card className="p-4 bg-background/70 border border-primary/10">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Avg Duration</p>
                    <p className="text-2xl font-bold">{stats.avgDuration.toFixed(2)} ms</p>
                  </div>
                  <Clock className="h-8 w-8 text-primary opacity-70" />
                </div>
              </Card>
            </div>
            
            {/* Success/Failure Distribution */}
            <Card className="p-4 bg-background/70 border border-primary/10">
              <CardTitle className="text-lg mb-4 flex items-center gap-2">
                <PieChart className="h-5 w-5 text-primary" />
                Success/Failure Distribution
              </CardTitle>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={statusData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={80}
                      paddingAngle={5}
                      dataKey="value"
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    >
                      {statusData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </Card>
            
            {/* Recent Actions */}
            <Card className="p-4 bg-background/70 border border-primary/10">
              <CardTitle className="text-lg mb-4 flex items-center gap-2">
                <Activity className="h-5 w-5 text-primary" />
                Recent Actions
              </CardTitle>
              <ScrollArea className="h-64 pr-4">
                {actions.slice(0, 8).map((action) => (
                  <Card key={action.id} className="mb-2 p-3 bg-background/50 border border-primary/5">
                    <div className="flex justify-between">
                      <div className="flex gap-2 items-center">
                        {getStatusIcon(action.status)}
                        <span className="font-medium">{action.actionType}</span>
                      </div>
                      <Badge className={getStatusColor(action.status)}>
                        {action.status}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      <span>Agent: {action.agentType}</span>
                      <span className="ml-2">|</span>
                      <span className="ml-2">Time: {formatDate(action.createdAt)}</span>
                    </div>
                    {action.duration !== null && action.duration !== undefined && (
                      <div className="text-xs text-muted-foreground">
                        Duration: {typeof action.duration === 'number' ? action.duration.toFixed(2) : action.duration} ms
                      </div>
                    )}
                    {action.errorMessage && (
                      <div className="text-xs text-red-500 mt-1">
                        Error: {action.errorMessage}
                      </div>
                    )}
                  </Card>
                ))}
              </ScrollArea>
            </Card>
          </TabsContent>
          
          {/* Action Log Tab */}
          <TabsContent value="actions">
            <ScrollArea className="h-[600px] pr-4">
              {actions.map((action) => (
                <Card key={action.id} className="mb-3 p-4 bg-background/70 border border-primary/10">
                  <div className="flex justify-between items-center">
                    <div className="flex gap-2 items-center">
                      {getStatusIcon(action.status)}
                      <span className="font-medium">{action.actionType}</span>
                    </div>
                    <Badge className={getStatusColor(action.status)}>
                      {action.status}
                    </Badge>
                  </div>
                  <div className="text-sm mt-2">
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-muted-foreground">
                      <div>Agent ID: {action.agentId}</div>
                      <div>Type: {action.agentType}</div>
                      {action.duration !== null && action.duration !== undefined && 
                        <div>Duration: {typeof action.duration === 'number' ? action.duration.toFixed(2) : action.duration} ms</div>
                      }
                    </div>
                    <div className="text-xs text-muted-foreground mt-1">
                      {formatDate(action.createdAt)}
                    </div>
                  </div>
                  {action.errorMessage && (
                    <div className="text-sm text-red-500 mt-2 p-2 bg-red-100/10 rounded">
                      {action.errorMessage}
                    </div>
                  )}
                  {action.metadata && Object.keys(action.metadata).length > 0 && (
                    <div className="mt-2 text-xs">
                      <p className="font-medium text-muted-foreground">Metadata:</p>
                      <pre className="p-2 bg-background/50 rounded overflow-x-auto">
                        {JSON.stringify(action.metadata, null, 2)}
                      </pre>
                    </div>
                  )}
                </Card>
              ))}
            </ScrollArea>
          </TabsContent>
          
          {/* Analytics Tab */}
          <TabsContent value="analytics" className="space-y-4">
            {/* Agent Type Performance */}
            <Card className="p-4 bg-background/70 border border-primary/10">
              <CardTitle className="text-lg mb-4 flex items-center gap-2">
                <Server className="h-5 w-5 text-primary" />
                Agent Type Performance
              </CardTitle>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={agentTypeData}>
                    <XAxis dataKey="name" />
                    <YAxis yAxisId="left" orientation="left" stroke="#8884d8" />
                    <YAxis yAxisId="right" orientation="right" stroke="#82ca9d" />
                    <Tooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="count" name="Action Count" fill="#8884d8" />
                    <Bar yAxisId="right" dataKey="successRate" name="Success Rate (%)" fill="#82ca9d" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
            
            {/* Action Type Performance */}
            <Card className="p-4 bg-background/70 border border-primary/10">
              <CardTitle className="text-lg mb-4 flex items-center gap-2">
                <BarChart3 className="h-5 w-5 text-primary" />
                Action Type Performance
              </CardTitle>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={actionTypeData}>
                    <XAxis dataKey="name" />
                    <YAxis yAxisId="left" orientation="left" stroke="#8884d8" />
                    <YAxis yAxisId="right" orientation="right" stroke="#82ca9d" />
                    <Tooltip />
                    <Legend />
                    <Bar yAxisId="left" dataKey="count" name="Action Count" fill="#8884d8" />
                    <Bar yAxisId="right" dataKey="successRate" name="Success Rate (%)" fill="#82ca9d" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}

export default AgentMonitoring;