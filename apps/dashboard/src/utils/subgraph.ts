import { createClient, defaultExchanges, subscriptionExchange } from 'urql';
import { createClient as createWSClient } from 'graphql-ws';

// Types for subgraph responses
export interface Token {
  id: string;
  symbol: string;
  name: string;
  decimals: number;
  totalSupply: string;
  volume: string;
  volumeUSD: string;
  txCount: string;
  liquidity: string;
  derivedETH: string;
}

export interface Pair {
  id: string;
  token0: Token;
  token1: Token;
  reserve0: string;
  reserve1: string;
  reserveUSD: string;
  volumeUSD: string;
  txCount: string;
}

export interface PairDayData {
  id: string;
  date: number;
  pairAddress: string;
  token0: Token;
  token1: Token;
  reserve0: string;
  reserve1: string;
  reserveUSD: string;
  volumeToken0: string;
  volumeToken1: string;
  volumeUSD: string;
  txCount: string;
}

// WebSocket client for subscriptions
const wsClient = createWSClient({
  url: import.meta.env.VITE_SUBGRAPH_WS_ENDPOINT || 
       import.meta.env.VITE_SUBGRAPH_ENDPOINT?.replace('http', 'ws') || 
       'wss://api.studio.thegraph.com/query/your-id/sonic-blockchain/version',
});

// Create GraphQL client with subscriptions support
export const client = createClient({
  url: import.meta.env.VITE_SUBGRAPH_ENDPOINT || 'https://api.studio.thegraph.com/query/your-id/sonic-blockchain/version',
  exchanges: [
    ...defaultExchanges,
    subscriptionExchange({
      forwardSubscription: (operation) => ({
        subscribe: (sink) => ({
          unsubscribe: wsClient.subscribe(operation, sink),
        }),
      }),
    }),
  ],
});

// Common GraphQL queries
export const TOKENS_QUERY = `
  query GetTokens($first: Int = 100, $orderBy: String = "volumeUSD", $orderDirection: String = "desc") {
    tokens(first: $first, orderBy: $orderBy, orderDirection: $orderDirection) {
      id
      symbol
      name
      decimals
      totalSupply
      volume
      volumeUSD
      txCount
      liquidity
      derivedETH
    }
  }
`;

export const PAIRS_QUERY = `
  query GetPairs($first: Int = 100, $orderBy: String = "reserveUSD", $orderDirection: String = "desc") {
    pairs(first: $first, orderBy: $orderBy, orderDirection: $orderDirection) {
      id
      token0 {
        id
        symbol
        name
      }
      token1 {
        id
        symbol
        name
      }
      reserve0
      reserve1
      reserveUSD
      volumeUSD
      txCount
    }
  }
`;

export const TOKEN_DAY_DATA_QUERY = `
  query GetTokenDayData($tokenId: String!, $days: Int = 7) {
    tokenDayDatas(
      first: $days,
      orderBy: "date",
      orderDirection: "desc",
      where: { token: $tokenId }
    ) {
      id
      date
      priceUSD
      volumeUSD
      liquidityUSD
      txCount
    }
  }
`;

// Helper functions for common data fetching patterns
export const fetchTopTokens = async (count: number = 100) => {
  const { data } = await client.query(TOKENS_QUERY, { first: count }).toPromise();
  return data?.tokens || [];
};

export const fetchTopPairs = async (count: number = 100) => {
  const { data } = await client.query(PAIRS_QUERY, { first: count }).toPromise();
  return data?.pairs || [];
};

export const fetchTokenHistory = async (tokenId: string, days: number = 7) => {
  const { data } = await client.query(TOKEN_DAY_DATA_QUERY, { tokenId, days }).toPromise();
  return data?.tokenDayDatas || [];
};

// Hook for real-time data subscription
export const useTokenData = (tokenId: string) => {
  const TOKEN_SUBSCRIPTION = `
    subscription TokenUpdate($id: String!) {
      token(id: $id) {
        id
        volumeUSD
        liquidity
        derivedETH
        txCount
      }
    }
  `;

  return client.subscription(TOKEN_SUBSCRIPTION, { id: tokenId });
};
