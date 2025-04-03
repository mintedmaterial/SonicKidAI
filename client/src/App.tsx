import { Route, Switch } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import NotFound from "@/pages/not-found";
import Home from "@/pages/home";
import Chat from "@/pages/chat";
import Dashboard from "@/pages/Dashboard";
import EnhancedDashboard from "@/pages/EnhancedDashboard";
import ChartAnalysisPage from "@/pages/ChartAnalysisPage";
import { Link, useLocation } from "wouter";
import { useEffect } from "react";

function Navigation() {
  const [location] = useLocation();
  
  return (
    <nav className="bg-background border-b mb-4">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <span className="font-bold text-xl mr-8">
              <span className="text-pink-500">SonicKid</span> <span className="text-primary">AI</span>
            </span>
            <div className="flex items-center space-x-4">
              <Link href="/" className={`font-medium hover:text-primary ${location === '/' ? 'text-primary' : ''}`}>
                Home
              </Link>
              <Link href="/dashboard" className={`font-medium hover:text-primary ${location === '/dashboard' ? 'text-primary' : ''}`}>
                Dashboard
              </Link>
              <Link href="/enhanced-dashboard" className={`font-medium hover:text-primary ${location === '/enhanced-dashboard' ? 'text-primary' : ''}`}>
                Enhanced Dashboard
              </Link>
              <Link href="/chat" className={`font-medium hover:text-primary ${location === '/chat' ? 'text-primary' : ''}`}>
                Chat
              </Link>
              <Link href="/chart-analysis" className={`font-medium hover:text-primary ${location === '/chart-analysis' ? 'text-primary' : ''}`}>
                Chart Analysis
              </Link>
            </div>
          </div>
        </div>
      </div>
    </nav>
  );
}

function Router() {
  useEffect(() => {
    console.log("Router component loaded");
  }, []);

  return (
    <>
      <Navigation />
      <Switch>
        <Route path="/">
          <div className="container mx-auto px-4">
            <Home />
          </div>
        </Route>
        <Route path="/dashboard">
          <div className="container mx-auto px-4">
            <Dashboard />
          </div>
        </Route>
        <Route path="/enhanced-dashboard">
          <EnhancedDashboard />
        </Route>
        <Route path="/chat">
          <div className="container mx-auto px-4">
            <Chat />
          </div>
        </Route>
        <Route path="/chart-analysis">
          <div className="container mx-auto px-4">
            <ChartAnalysisPage />
          </div>
        </Route>
        <Route path="/:rest*">
          <div className="container mx-auto px-4">
            <NotFound />
          </div>
        </Route>
      </Switch>
    </>
  );
}

function App() {
  useEffect(() => {
    console.log("SonicKid AI Dashboard loaded");
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <Router />
      <Toaster />
    </QueryClientProvider>
  );
}

export default App;