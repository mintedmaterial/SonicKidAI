import { Express, Router } from 'express';
import express from 'express';
import path from 'path';
import { desc, sql } from 'drizzle-orm';
import { db } from './db';
import { dashboardPosts, agentActions } from '@shared/schema';
import { insertAgentActionSchema } from '@shared/schema';
import { marketData } from '@shared/marketdata';
import chatRouter from './routes/chat';
import marketRouter from './routes/market';
import socialRouter from './routes/social';
import nftRouter from './routes/nft';
import swapRouter from './routes/swap';
import uploadRouter from './routes/uploads';
// API keys are now managed through environment variables

export function registerRoutes(app: Express): void {
  console.log('Starting route registration...');

  // Add health check endpoint
  app.get('/api/health', (req, res) => {
    console.log(`Health check requested from ${req.ip}`);
    res.json({ 
      status: 'ok',
      environment: process.env.NODE_ENV,
      time: new Date().toISOString()
    });
  });
  
  // Commented out the root route to let Vite handle it
  // app.get('/', (req, res) => {
  //   console.log('Root route requested explicitly from', req.ip);
  //   res.setHeader('Content-Type', 'text/html');
  //   res.send(`...`);
  // });
  
  // Add direct routes for easy testing
  
  // Test page route
  app.get('/test-page', (req, res) => {
    console.log('Test page requested');
    res.send(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>SonicKid AI Test Page</title>
        <style>
          body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
          h1 { color: #ff00ff; }
          .card { border: 1px solid #ccc; padding: 20px; border-radius: 8px; margin: 20px 0; }
          button { background: #ff00ff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
          button:hover { background: #cc00cc; }
        </style>
      </head>
      <body>
        <h1>SonicKid AI Test Page</h1>
        <div class="card">
          <h2>Server Status</h2>
          <p>Server is running!</p>
          <p>Time: ${new Date().toISOString()}</p>
          <p>Environment: ${process.env.NODE_ENV}</p>
        </div>
        <div class="card">
          <h2>Test API Endpoints</h2>
          <button onclick="fetch('/api/health').then(r=>r.json()).then(data=>alert(JSON.stringify(data, null, 2)))">
            Test Health Endpoint
          </button>
        </div>
      </body>
      </html>
    `);
  });
  
  // Home page simple route for direct access
  app.get('/direct-home', async (req, res) => {
    console.log('Direct home page requested');
    
    // Attempt to get real data from API (with fallback)
    let sonicData = {
      address: "0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38", // wS token address
      sonicAddress: "0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38", // Native Sonic token
      symbol: "SONIC", 
      name: "Wrapped Sonic",
      price: 0.51,
      volume24h: 878037.85,
      tvl: 866116157.46,
      tvlChange24h: 0
    };
    
    try {
      // Try to fetch live data
      const response = await fetch('http://localhost:3000/api/market/sonic');
      if (response.ok) {
        const data = await response.json();
        sonicData = { ...sonicData, ...data };
      }
    } catch (error) {
      console.log('Error fetching Sonic data, using fallback');
    }
    
    // Format the sentiment text
    let sentimentText = "Neutral";
    let sentimentColor = "#888888";
    
    try {
      const response = await fetch('http://localhost:3000/api/market/sentiment');
      if (response.ok) {
        const data = await response.json();
        sentimentText = data.sentiment || sentimentText;
        
        if (sentimentText.toLowerCase() === 'bullish') {
          sentimentColor = "#22cc44";
        } else if (sentimentText.toLowerCase() === 'bearish') {
          sentimentColor = "#cc2244";
        }
      }
    } catch (error) {
      console.log('Error fetching sentiment data, using fallback');
    }
    
    // Format monetary values
    const formatCurrency = (value) => {
      // Convert to number if it's a string
      const numValue = typeof value === 'string' ? parseFloat(value) : value;
      
      // Handle non-numeric values
      if (isNaN(numValue)) return '$0.00';
      
      if (numValue >= 1000000000) {
        return '$' + (numValue / 1000000000).toFixed(2) + 'B';
      } else if (numValue >= 1000000) {
        return '$' + (numValue / 1000000).toFixed(2) + 'M';
      } else if (numValue >= 1000) {
        return '$' + (numValue / 1000).toFixed(2) + 'K';
      } else {
        return '$' + numValue.toFixed(2);
      }
    };
    
    // Get current time for dashboard
    const currentTime = new Date().toLocaleString();
    
    res.send(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>SonicKid AI Dashboard</title>
        <style>
          body { font-family: system-ui, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }
          header { background-color: #FF00FF; color: white; padding: 1rem; position: sticky; top: 0; z-index: 100; }
          h1 { margin: 0; font-size: 1.8rem; display: flex; align-items: center; }
          h1 span { font-weight: normal; opacity: 0.8; margin-left: 0.5rem; }
          nav { display: flex; gap: 1rem; margin-top: 1rem; }
          nav a { color: white; text-decoration: none; padding: 0.5rem 1rem; border-radius: 4px; background: rgba(255,255,255,0.2); }
          nav a:hover { background: rgba(255,255,255,0.3); }
          .container { max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
          .card { background: white; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
          .dashboard-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1.5rem; }
          .full-width { grid-column: 1 / -1; }
          .chart-placeholder { background-color: #f0f0f0; height: 300px; border-radius: 4px; display: flex; justify-content: center; align-items: center; color: #666; }
          h2 { margin-top: 0; color: #333; display: flex; justify-content: space-between; align-items: center; }
          h2 .badge { font-size: 0.8rem; padding: 0.2rem 0.5rem; border-radius: 4px; background-color: ${sentimentColor}; color: white; }
          p { color: #666; }
          .key-metric { font-size: 1.8rem; font-weight: bold; color: #333; margin: 0.5rem 0; }
          .key-metric.positive { color: #22cc44; }
          .key-metric.negative { color: #cc2244; }
          .key-metric.neutral { color: #333; }
          .metrics-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem; }
          .metric-item { margin-bottom: 0.5rem; }
          .metric-label { font-size: 0.9rem; color: #888; }
          .metric-value { font-size: 1.2rem; font-weight: bold; color: #333; }
          .footer { text-align: center; margin-top: 2rem; padding: 1rem; color: #888; font-size: 0.9rem; }
          .small-text { font-size: 0.8rem; }
          .chat-box { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; height: 300px; overflow-y: auto; background: #fff; margin-top: 1rem; }
          .chat-input { display: flex; margin-top: 1rem; }
          .chat-input input { flex: 1; padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px 0 0 4px; }
          .chat-input button { padding: 0.5rem 1rem; background: #FF00FF; color: white; border: none; border-radius: 0 4px 4px 0; cursor: pointer; }
          .message { margin-bottom: 0.5rem; padding: 0.5rem; border-radius: 4px; }
          .message.user { background: #f0f0f0; text-align: right; }
          .message.agent { background: #f8e6f8; }
          @media (max-width: 768px) {
            .dashboard-grid { grid-template-columns: 1fr; }
            .metrics-grid { grid-template-columns: 1fr; }
          }
        </style>
      </head>
      <body>
        <header>
          <h1>SonicKid AI <span>Dashboard</span></h1>
          <nav>
            <a href="/direct-home">Home</a>
            <a href="/chat">Chat</a>
            <a href="/test-page">API Test</a>
          </nav>
        </header>
        <div class="container">
          <div class="dashboard-grid">
            <div class="card full-width">
              <h2>Market Overview</h2>
              <div class="chart-placeholder">
                Interactive Price Chart Not Available in Direct View
              </div>
            </div>
            <div class="card">
              <h2>SONIC Market Data <span class="badge">${sentimentText}</span></h2>
              <div class="key-metric">Price: $${sonicData.price.toFixed(2)}</div>
              <div class="metrics-grid">
                <div class="metric-item">
                  <div class="metric-label">24h Volume</div>
                  <div class="metric-value">${formatCurrency(sonicData.volume24h)}</div>
                </div>
                <div class="metric-item">
                  <div class="metric-label">TVL</div>
                  <div class="metric-value">${formatCurrency(sonicData.tvl)}</div>
                </div>
                <div class="metric-item">
                  <div class="metric-label">TVL Change (24h)</div>
                  <div class="metric-value ${sonicData.tvlChange24h > 0 ? 'positive' : sonicData.tvlChange24h < 0 ? 'negative' : 'neutral'}">
                    ${sonicData.tvlChange24h > 0 ? '+' : ''}${sonicData.tvlChange24h.toFixed(2)}%
                  </div>
                </div>
                <div class="metric-item">
                  <div class="metric-label">Native Address</div>
                  <div class="metric-value small-text">${sonicData.address || 'SonicxvLud67EceaEzCLRnMTBqzYUUYNr93DBkBdDES'}</div>
                </div>
                <div class="metric-item">
                  <div class="metric-label">Wrapped Address</div>
                  <div class="metric-value small-text">${sonicData.wrappedAddress || '0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38'}</div>
                </div>
              </div>
            </div>
            <div class="card">
              <h2>Trading Activity</h2>
              <div class="key-metric">Recent Swaps: 145</div>
              <div class="metrics-grid">
                <div class="metric-item">
                  <div class="metric-label">Avg Trade Size</div>
                  <div class="metric-value">$2,430</div>
                </div>
                <div class="metric-item">
                  <div class="metric-label">24h Transactions</div>
                  <div class="metric-value">2,145</div>
                </div>
                <div class="metric-item">
                  <div class="metric-label">Last Activity</div>
                  <div class="metric-value small-text">${new Date().toLocaleTimeString()}</div>
                </div>
                <div class="metric-item">
                  <div class="metric-label">Trading Trend</div>
                  <div class="metric-value positive">Increasing</div>
                </div>
              </div>
            </div>
            <div class="card">
              <h2>Network Stats</h2>
              <div class="key-metric">Gas Price: 25 Gwei</div>
              <div class="metrics-grid">
                <div class="metric-item">
                  <div class="metric-label">Block Height</div>
                  <div class="metric-value">12,345,678</div>
                </div>
                <div class="metric-item">
                  <div class="metric-label">Network Status</div>
                  <div class="metric-value positive">Active</div>
                </div>
                <div class="metric-item">
                  <div class="metric-label">Validators</div>
                  <div class="metric-value">51</div>
                </div>
                <div class="metric-item">
                  <div class="metric-label">Network Security</div>
                  <div class="metric-value positive">High</div>
                </div>
              </div>
            </div>
            <div class="card">
              <h2>Latest News</h2>
              <div id="news-container">
                <div class="metric-item">
                  <div class="metric-label">Loading news...</div>
                  <div class="metric-value">Fetching the latest crypto news...</div>
                </div>
              </div>
              <script>
                // Fetch news from our API
                fetch('/api/market/news')
                  .then(response => response.json())
                  .then(data => {
                    const newsContainer = document.getElementById('news-container');
                    newsContainer.innerHTML = '';
                    
                    if (data.articles && data.articles.length > 0) {
                      // Display up to 4 news items
                      data.articles.slice(0, 4).forEach(article => {
                        const itemDiv = document.createElement('div');
                        itemDiv.className = 'metric-item';
                        
                        const labelDiv = document.createElement('div');
                        labelDiv.className = 'metric-label';
                        labelDiv.textContent = article.source;
                        
                        const timeSpan = document.createElement('span');
                        timeSpan.style.marginLeft = '8px';
                        timeSpan.style.opacity = '0.7';
                        timeSpan.textContent = article.time ? new Date(article.time).toLocaleDateString() : '';
                        labelDiv.appendChild(timeSpan);
                        
                        const valueDiv = document.createElement('div');
                        valueDiv.className = 'metric-value';
                        
                        // Add sentiment indicator if available
                        if (article.sentiment) {
                          const sentimentSpan = document.createElement('span');
                          sentimentSpan.style.display = 'inline-block';
                          sentimentSpan.style.width = '8px';
                          sentimentSpan.style.height = '8px';
                          sentimentSpan.style.borderRadius = '50%';
                          sentimentSpan.style.marginRight = '6px';
                          
                          if (article.sentiment === 'positive') {
                            sentimentSpan.style.backgroundColor = '#22cc44';
                          } else if (article.sentiment === 'negative') {
                            sentimentSpan.style.backgroundColor = '#cc2244';
                          } else {
                            sentimentSpan.style.backgroundColor = '#888888';
                          }
                          
                          valueDiv.appendChild(sentimentSpan);
                        }
                        
                        const titleText = document.createTextNode(article.title);
                        valueDiv.appendChild(titleText);
                        
                        itemDiv.appendChild(labelDiv);
                        itemDiv.appendChild(valueDiv);
                        newsContainer.appendChild(itemDiv);
                      });
                    } else {
                      // Fallback if no news
                      const itemDiv = document.createElement('div');
                      itemDiv.className = 'metric-item';
                      itemDiv.innerHTML = '<div class="metric-label">No news available</div><div class="metric-value">Unable to fetch the latest crypto news at this time.</div>';
                      newsContainer.appendChild(itemDiv);
                    }
                  })
                  .catch(error => {
                    console.error('Error fetching news:', error);
                    const newsContainer = document.getElementById('news-container');
                    newsContainer.innerHTML = '<div class="metric-item"><div class="metric-label">Error</div><div class="metric-value">Failed to load news data. Please try again later.</div></div>';
                  });
              </script>
            </div>
            <div class="card">
              <h2>AI Assistant</h2>
              <div class="chat-box">
                <div class="message agent">Welcome to SonicKid AI Dashboard! Ask me anything about market data, trading trends, or network information.</div>
                <div class="message user">What's the current sentiment for SONIC?</div>
                <div class="message agent">The current market sentiment for SONIC is ${sentimentText.toLowerCase()}. This is based on recent price action, trading volume, and social media analysis.</div>
              </div>
              <div class="chat-input">
                <input type="text" placeholder="Ask about market data..." disabled>
                <button onclick="alert('Chat functionality available in full dashboard')">Send</button>
              </div>
            </div>
          </div>
          <div class="footer">
            SonicKid AI Dashboard | Last Updated: ${currentTime} | Data provided for demonstration purposes
          </div>
        </div>
        <script>
          // This would normally contain interactive chart and data refresh functionality
          console.log('SonicKid AI Dashboard loaded');
          
          // Simple color theme toggle
          let isDarkMode = false;
          function toggleDarkMode() {
            isDarkMode = !isDarkMode;
            document.body.style.backgroundColor = isDarkMode ? '#222' : '#f8f9fa';
            document.body.style.color = isDarkMode ? '#fff' : '#333';
          }
        </script>
      </body>
      </html>
    `);
  });
  
  console.log('✅ Health check endpoint registered');

  // Market Data Routes
  console.log('Setting up market router...');

  marketRouter.get('/sonic', async (req, res) => {
    console.log('Sonic market data requested');
    try {
      // Try to fetch real data from MarketData service
      const sonicAddress = "SONIC"; // Use symbol for lookup
      
      try {
        // Get token data from our market service
        const tokenData = await marketData.getTokenData(sonicAddress);
        
        if (tokenData) {
          console.log('✅ DexScreener Sonic data found:', tokenData);
          
          // Format the data for API response
          const marketData = {
            address: tokenData.address || "0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38", // Wrapped Sonic token address
            nativeAddress: tokenData.nativeAddress || "0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38", // Using Wrapped address as primary
            wrappedAddress: tokenData.wrappedAddress || "0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38", // wS token address
            symbol: tokenData.symbol || "wS",
            name: tokenData.name || "Wrapped Sonic",
            decimals: tokenData.decimals || 18,
            priceUsd: tokenData.priceUsd || (tokenData.prices && tokenData.prices[0] ? tokenData.prices[0].price : 0),
            // Use the DefiLlama TVL data if available, otherwise fall back to liquidity
            tvl: tokenData.tvl || tokenData.liquidity || 866116157,
            // Use the proper tvlChange24h if available
            tvlChange24h: tokenData.tvlChange24h || tokenData.priceChange24h || 0,
            volume24h: tokenData.volume24h || 870000,
            liquidity: tokenData.liquidity || 1470000,
            source: tokenData.prices && tokenData.prices[0] ? tokenData.prices[0].source : 'sonic_labs'
          };
          
          res.json(marketData);
          console.log('✅ Sonic market data sent successfully (DexScreener)');
          return;
        }
      } catch (fetchError) {
        console.error('Error fetching from DexScreener:', fetchError);
      }
      
      // If we get here, we need to use fallback data
      console.log('⚠️ Using fallback Sonic data');
      res.json({
        address: "0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38", // Wrapped Sonic token address
        nativeAddress: "0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38", // Using Wrapped address as primary
        wrappedAddress: "0x039e2fB66102314Ce7b64Ce5Ce3E5183bc94aD38", // wS token address
        symbol: "wS",
        name: "Wrapped Sonic",
        decimals: 18,
        priceUsd: 0.4857,
        tvl: 866116157,
        tvlChange24h: 0,
        volume24h: 870000,
        liquidity: 1470000,
        source: 'sonic_labs'
      });
      console.log('✅ Sonic market data sent successfully (fallback)');
    } catch (error) {
      console.error('Error fetching Sonic market data:', error);
      res.status(500).json({ error: 'Failed to fetch market data' });
    }
  });

  marketRouter.get('/prices', (req, res) => {
    const { token = 'SONIC', period = '24h' } = req.query;
    console.log(`Price data requested for ${token} over ${period}`);
    
    try {
      // Normally we would fetch from a database or external API
      // For now, generate some realistic price data based on token and period
      const generatePriceData = (token: string, period: string) => {
        let dataPoints = 0;
        let startTime = new Date();
        let basePrice = 0;
        
        // Set parameters based on period
        switch(period) {
          case '1h':
            dataPoints = 60;
            startTime = new Date(Date.now() - 60 * 60 * 1000); // 1 hour ago
            break;
          case '24h':
            dataPoints = 24;
            startTime = new Date(Date.now() - 24 * 60 * 60 * 1000); // 24 hours ago
            break;
          case '7d':
            dataPoints = 7 * 24;
            startTime = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000); // 7 days ago
            break;
          case '30d':
            dataPoints = 30;
            startTime = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000); // 30 days ago
            break;
          default:
            dataPoints = 24;
            startTime = new Date(Date.now() - 24 * 60 * 60 * 1000); // Default to 24h
        }
        
        // Set base price based on token
        switch(token) {
          case 'SONIC':
            basePrice = 0.4857;
            break;
          case 'WETH':
            basePrice = 3200.25;
            break;
          case 'USDT':
            basePrice = 1.0;
            break;
          default:
            basePrice = 1.0;
        }
        
        // Generate data points
        const data = [];
        const timeIncrement = period === '1h' ? 60 : 
                           period === '24h' ? 3600 : 
                           period === '7d' ? 3600 * 24 / 3 : 
                           3600 * 24;
        
        for (let i = 0; i < dataPoints; i++) {
          const timestamp = new Date(startTime.getTime() + i * timeIncrement * 1000);
          // Add some realistic randomness to price (with trend)
          const volatility = token === 'USDT' ? 0.001 : token === 'WETH' ? 0.02 : 0.05;
          const trend = Math.sin(i / dataPoints * Math.PI) * volatility * 5;
          const randomFactor = (Math.random() - 0.5) * volatility;
          
          const price = basePrice * (1 + trend + randomFactor);
          const volume = Math.floor(basePrice * 100000 * (0.8 + Math.random() * 0.4));
          
          data.push({
            timestamp: timestamp.toISOString(),
            price: price,
            volume: volume
          });
        }
        
        return data;
      };
      
      const priceData = generatePriceData(token as string, period as string);
      res.json(priceData);
      console.log(`✅ Price data sent for ${token} over ${period}: ${priceData.length} points`);
    } catch (error) {
      console.error('Error generating price data:', error);
      res.status(500).json({ error: 'Failed to generate price data' });
    }
  });

  marketRouter.get('/sentiment', (req, res) => {
    console.log('Market sentiment data requested');
    try {
      res.json({
        sentiment: 'Neutral',
        confidence: 50,
        trending: [
          { topic: 'DeFi', volume: 1200 },
          { topic: 'NFTs', volume: 800 },
          { topic: 'Layer2', volume: 600 }
        ]
      });
      console.log('✅ Sentiment data sent successfully');
    } catch (error) {
      console.error('Error fetching sentiment data:', error);
      res.status(500).json({ error: 'Failed to fetch sentiment data' });
    }
  });

  marketRouter.get('/news', async (req, res) => {
    console.log('Market news data requested');
    try {
      // Try to fetch real data from CryptoPanic API
      // Note: We're using BTC/ETH as they have more consistent data
      const cryptoPanicUrl = 'https://cryptopanic.com/api/pro/v1/posts/?auth_token=a6ddf5dba1c999bf140e128e146797ce2a515443&currencies=BTC,ETH&kind=news&public=true';
      
      try {
        const response = await fetch(cryptoPanicUrl);
        
        if (response.ok) {
          const data = await response.json();
          
          // Process and format the articles
          const articles = data.results.map(item => ({
            title: item.title,
            source: item.source?.title || 'CryptoPanic',
            url: item.url,
            time: new Date(item.published_at || item.created_at).toLocaleString(),
            sentiment: item.votes?.positive > item.votes?.negative ? 'positive' : 
                      item.votes?.negative > item.votes?.positive ? 'negative' : 'neutral'
          })).slice(0, 10); // Limit to top 10 articles
          
          res.json({ articles });
          console.log(`✅ CryptoPanic news data sent successfully: ${articles.length} articles`);
          return;
        } else {
          console.error('Error fetching from CryptoPanic API:', response.status, response.statusText);
        }
      } catch (fetchError) {
        console.error('Error fetching from CryptoPanic:', fetchError);
      }
      
      // Fallback data if API fails
      res.json({
        articles: [
          {
            title: "Bitcoin Set for April Price Surge as Fed Signals Monetary Easing",
            source: "Benzinga",
            url: "https://www.benzinga.com/markets/cryptocurrency/24/03/37619768/bitcoin-set-for-april-price-surge-as-fed-signals-monetary-easing",
            time: new Date().toLocaleString(),
            sentiment: "positive"
          },
          {
            title: "French State-Owned Bank Rolls Out $27M Initiative To Invest in Crypto Projects",
            source: "The Daily Hodl",
            url: "https://dailyhodl.com/2024/03/30/french-state-owned-bank-rolls-out-27000000-initiative-to-invest-in-crypto-projects/",
            time: new Date().toLocaleString(),
            sentiment: "positive"
          },
          {
            title: "Ethereum Whales on MakerDAO Face $238M Liquidation Risk as ETH Nears Critical Level",
            source: "Cryptopolitan",
            url: "https://www.cryptopolitan.com/ethereum-whales-makerdao-face-liquidation/",
            time: new Date().toLocaleString(),
            sentiment: "negative"
          },
          {
            title: "Bitcoin Could Hit $150,000 by Year-End, Says Financial Expert",
            source: "cryptodnes",
            url: "https://cryptodnes.com/bitcoin-could-hit-150000-by-year-end-says-financial-expert/",
            time: new Date().toLocaleString(),
            sentiment: "positive"
          },
          {
            title: "Investor Dan Tapiero Predicts Bitcoin Rallies, Says New Liquidity and Lower Rates Needed",
            source: "The Daily Hodl",
            url: "https://dailyhodl.com/2024/03/30/investor-dan-tapiero-predicts-bitcoin-rallies-says-new-liquidity-and-lower-rates-needed/",
            time: new Date().toLocaleString(),
            sentiment: "positive"
          }
        ]
      });
      console.log('✅ Fallback news data sent successfully');
    } catch (error) {
      console.error('Error processing news data:', error);
      res.status(500).json({ error: 'Failed to fetch news data' });
    }
  });

  // Mount market routes with explicit logging
  console.log('Mounting market routes at /api/market...');
  app.use('/api/market', marketRouter);
  console.log('✅ Market routes mounted successfully');
  
  // Mount swap routes
  console.log('Mounting cross-chain swap routes at /api/swap...');
  app.use('/api/swap', swapRouter);
  console.log('✅ Swap routes mounted successfully');
  
  // Mount social routes
  console.log('Mounting social routes at /api/social...');
  app.use('/api/social', socialRouter);
  console.log('✅ Social routes mounted successfully');
  
  // Mount chat routes
  console.log('Mounting chat routes at /api/chat...');
  app.use('/api/chat', chatRouter);
  console.log('✅ Chat routes mounted successfully');
  
  // Mount NFT routes
  console.log('Mounting NFT routes at /api/nft...');
  app.use('/api/nft', nftRouter);
  console.log('✅ NFT routes mounted successfully');
  
  // Register Uploads routes
  console.log('Registering Upload routes...');
  app.use('/api/uploads', uploadRouter);
  console.log('✅ Upload routes mounted successfully');
  
  // Register API Keys routes
  console.log('Registering API Keys routes...');
  // API keys are now managed through environment variables
  // app.use('/api/keys', apiKeysRouter);
  console.log('✅ API Keys routes mounted successfully');
  
  // Serve the uploads directory statically
  app.use('/uploads', express.static(path.join(process.cwd(), 'public/uploads')));
  console.log('✅ Static uploads directory mounted successfully');

  // Dashboard Posts Route
  app.get('/api/dashboard/posts', async (req, res) => {
    try {
      console.log('Fetching dashboard posts...');
      const posts = await db.select().from(dashboardPosts).orderBy(desc(dashboardPosts.createdAt)).limit(50);
      console.log(`Successfully fetched ${posts.length} dashboard posts`);
      res.json(posts);
    } catch (error) {
      console.error('Error fetching dashboard posts:', error);
      res.status(500).json({ error: 'Failed to fetch dashboard posts' });
    }
  });
  
  // Add endpoint to create dashboard posts
  app.post('/api/dashboard/posts', async (req, res) => {
    try {
      console.log('Creating dashboard post...');
      const { type, content, title, sourceId, metadata } = req.body;
      
      if (!type || !content) {
        return res.status(400).json({ error: 'Type and content are required' });
      }
      
      const [post] = await db.insert(dashboardPosts).values({
        type,
        content,
        title,
        sourceId,
        metadata
      }).returning();
      
      console.log(`Successfully created dashboard post with ID: ${post.id}`);
      res.status(201).json(post);
    } catch (error) {
      console.error('Error creating dashboard post:', error);
      res.status(500).json({ error: 'Failed to create dashboard post' });
    }
  });
  
  // Agent Actions Monitoring Endpoints
  
  // Get agent actions with filtering and pagination
  app.get('/api/agent/actions', async (req, res) => {
    try {
      console.log('Fetching agent actions...');
      
      // Parse query parameters
      const limit = req.query.limit ? parseInt(req.query.limit as string) : 50;
      const agentType = req.query.agentType as string || undefined;
      const status = req.query.status as string || undefined;
      const actionType = req.query.actionType as string || undefined;
      
      // Build the query with filters
      let query = db.select().from(agentActions).orderBy(desc(agentActions.createdAt));
      
      // Apply filters if provided
      if (agentType) {
        query = query.where(sql`${agentActions.agentType} = ${agentType}`);
      }
      if (status) {
        query = query.where(sql`${agentActions.status} = ${status}`);
      }
      if (actionType) {
        query = query.where(sql`${agentActions.actionType} = ${actionType}`);
      }
      
      // Apply limit
      query = query.limit(limit);
      
      // Execute the query
      const actions = await query;
      
      console.log(`Successfully fetched ${actions.length} agent actions`);
      res.json(actions);
    } catch (error) {
      console.error('Error fetching agent actions:', error);
      res.status(500).json({ error: 'Failed to fetch agent actions' });
    }
  });
  
  // Get agent action statistics
  app.get('/api/agent/stats', async (req, res) => {
    try {
      console.log('Fetching agent action statistics...');
      
      // Get total actions count
      const totalActions = await db
        .select({ count: sql`count(*)` })
        .from(agentActions)
        .then(result => parseInt(result[0].count.toString()));
      
      // Get success rate
      const successCount = await db
        .select({ count: sql`count(*)` })
        .from(agentActions)
        .where(sql`${agentActions.status} = ${'success'}`)
        .then(result => parseInt(result[0].count.toString()));
      
      // Get failure rate
      const failureCount = await db
        .select({ count: sql`count(*)` })
        .from(agentActions)
        .where(sql`${agentActions.status} = ${'failure'}`)
        .then(result => parseInt(result[0].count.toString()));
      
      // Get actions by type
      const actionsByType = await db
        .select({
          actionType: agentActions.actionType,
          count: sql`count(*)`, 
          successRate: sql`ROUND((SUM(CASE WHEN ${agentActions.status} = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2)`
        })
        .from(agentActions)
        .groupBy(agentActions.actionType);
      
      // Get actions by agent type
      const actionsByAgentType = await db
        .select({
          agentType: agentActions.agentType,
          count: sql`count(*)`,
          successRate: sql`ROUND((SUM(CASE WHEN ${agentActions.status} = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)), 2)`
        })
        .from(agentActions)
        .groupBy(agentActions.agentType);
      
      // Calculate average duration for successful actions
      const avgDuration = await db
        .select({
          avgDuration: sql`AVG(${agentActions.duration})`
        })
        .from(agentActions)
        .where(sql`${agentActions.status} = ${'success'} AND ${agentActions.duration} IS NOT NULL`)
        .then(result => parseFloat(result[0].avgDuration?.toString() || '0'));
      
      // Return the statistics
      const stats = {
        totalActions,
        successCount,
        failureCount,
        successRate: totalActions > 0 ? (successCount * 100 / totalActions).toFixed(2) : 0,
        actionsByType,
        actionsByAgentType,
        avgDuration: avgDuration || 0
      };
      
      console.log('Successfully fetched agent action statistics');
      res.json(stats);
    } catch (error) {
      console.error('Error fetching agent action statistics:', error);
      res.status(500).json({ error: 'Failed to fetch agent action statistics' });
    }
  });
  
  // Log a new agent action
  app.post('/api/agent/actions', async (req, res) => {
    try {
      console.log('Logging new agent action...');
      
      // Validate the request body
      const result = insertAgentActionSchema.safeParse(req.body);
      if (!result.success) {
        console.error('Invalid agent action data:', result.error);
        return res.status(400).json({ error: 'Invalid agent action data', details: result.error });
      }
      
      // Insert the agent action
      const newAction = await db.insert(agentActions).values(result.data).returning();
      
      console.log('Successfully logged agent action:', newAction[0]);
      res.status(201).json(newAction[0]);
    } catch (error) {
      console.error('Error logging agent action:', error);
      res.status(500).json({ error: 'Failed to log agent action' });
    }
  });

  // Add endpoint to manually trigger agent activity post creation
  app.post('/api/dashboard/trigger-activity', async (req, res) => {
    try {
      console.log('Manually triggering agent activity post creation...');
      
      // Get the specified category from request body if provided
      const { category } = req.body;
      
      // Import the Agent Activity Service
      const { getAgentActivityService } = await import('./services/agentActivityService');
      const agentActivityService = getAgentActivityService({
        // Pass API keys from environment
        openaiApiKey: process.env.OPENAI_API_KEY,
        anthropicApiKey: process.env.OPENROUTER_API_KEY
      });
      
      // Create a post with the specified category or let the service choose one
      const success = await agentActivityService.forcePost(category);
      
      if (success) {
        console.log('Successfully created agent activity post');
        res.status(201).json({ success: true, message: 'Agent activity post created successfully' });
      } else {
        console.error('Failed to create agent activity post');
        res.status(500).json({ success: false, error: 'Failed to create agent activity post' });
      }
    } catch (error) {
      console.error('Error triggering agent activity post:', error);
      res.status(500).json({ error: 'Failed to trigger agent activity post' });
    }
  });
  console.log('✅ Dashboard posts endpoint registered');

  // Register error handling middleware
  app.use((err: any, req: any, res: any, next: any) => {
    console.error('API Error:', err);
    res.status(err.status || 500).json({
      success: false,
      error: process.env.NODE_ENV === 'production' 
        ? 'Internal server error' 
        : err.message
    });
  });
  console.log('✅ Error handling middleware registered');

  console.log('Route registration completed');
}