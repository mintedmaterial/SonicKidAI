#!/usr/bin/env node
/**
 * DexScreener API wrapper for searching token pairs
 * This script is a JavaScript version of dexscreener.ts for testing purposes
 */
import { searchPairs } from 'dexscreener-sdk';
import yargs from 'yargs';
import { hideBin } from 'yargs/helpers';

// Chain mappings (updated for Sonic)
const CHAIN_MAPPING = {
  sonic: "sonic",  // Use "sonic" if DexScreener supports it
  "146": "sonic",  // Correct numeric chain ID for Sonic
  fantom: "fantom",
  base: "base",
  ethereum: "ethereum",
};

/**
 * Format pairs consistently, with Sonic-specific tweaks
 * @param {Object} pair - Raw pair data from DexScreener API 
 * @param {string} chain - Chain name
 * @returns {Object|null} Formatted pair or null if invalid
 */
function formatPair(pair, chain) {
  const baseSymbol = (pair.baseToken?.symbol || "").toUpperCase();
  const quoteSymbol = (pair.quoteToken?.symbol || "").toUpperCase();
  
  // Log raw pair for debugging
  console.error(`Raw pair: ${JSON.stringify(pair, null, 2)}`);
  
  // Basic validation
  if (!pair.chainId || !pair.pairAddress || !baseSymbol || !quoteSymbol) {
    console.error(`Skipping invalid pair: ${pair.pairAddress}`);
    return null;
  }
  
  // Sonic-specific normalization (optional, adjust as needed)
  let normalizedBase = baseSymbol;
  let normalizedQuote = quoteSymbol;
  if (chain === "sonic") {
    // Handle Sonic token (S, SONIC, WSONIC) as quote
    if (["S", "SONIC", "WSONIC"].includes(quoteSymbol)) {
      normalizedQuote = "wS"; // Standardize to wS
    } else if (["S", "SONIC", "WSONIC"].includes(baseSymbol)) {
      // Swap if Sonic is base (e.g., S/Metro → Metro/wS)
      normalizedBase = quoteSymbol;
      normalizedQuote = "wS";
    }
    
    // Handle USDC variants
    if (quoteSymbol.includes("USDC")) {
      normalizedQuote = "USDC.e";
    }
    
    // Remove "W" prefix from base tokens (e.g., WMETRO → METRO)
    if (normalizedBase.startsWith("W") && normalizedBase !== "WSONIC") {
      normalizedBase = normalizedBase.substring(1);
    }
  }
  
  return {
    pair: `${normalizedBase}/${normalizedQuote}`,
    chain,
    chainId: pair.chainId,
    baseToken: { symbol: normalizedBase, address: pair.baseToken?.address || "" },
    quoteToken: { symbol: normalizedQuote, address: pair.quoteToken?.address || "" },
    price: parseFloat(pair.priceNative || "0"),
    priceUsd: parseFloat(pair.priceUsd || "0"),
    priceChange24h: parseFloat(pair.priceChange?.h24 || "0"),
    volume24h: parseFloat(pair.volume?.h24 || "0"),
    liquidity: parseFloat(pair.liquidity?.usd || "0"),
    pairAddress: pair.pairAddress || "",
  };
}

/**
 * Search for pairs using DexScreener SDK
 * @param {string} query - Search query (token name)
 * @param {string} chainId - Chain identifier
 */
async function search(query, chainId) {
  try {
    console.error(`Searching for pairs with query: ${query}, chainId: ${chainId}`);
    const dexChainId = CHAIN_MAPPING[chainId] || chainId;
    console.error(`Using DexScreener chain ID: ${dexChainId}`);
    
    // Search with chain-specific query
    const response = await searchPairs(`${query} chain:${dexChainId}`);
    console.error(`Raw API response: ${JSON.stringify(response, null, 2)}`);
    
    if (!response?.pairs?.length) {
      console.error("No pairs found in API response");
      console.log("[]");
      return;
    }
    
    // Filter pairs to match Sonic chain and query
    console.error(`Original pairs count: ${response.pairs.length}`);
    
    // Step 1: Filter by chain - be more flexible with Sonic chain ID
    const chainFilteredPairs = response.pairs.filter(pair => {
      // For Sonic chain, accept both "sonic" and numeric "146" chain IDs
      let isMatch = false;
      
      // Looking specifically for Sonic chain
      if (dexChainId === "sonic" || dexChainId === "146") {
        // Accept either "sonic" or "146" as valid Sonic chain IDs
        isMatch = pair.chainId === "sonic" || 
                 pair.chainId === "146" || 
                 // Some APIs return "fantom" for Sonic pairs
                 (pair.chainId === "fantom" && 
                  (pair.baseToken?.symbol?.toUpperCase() === "SONIC" || 
                   pair.quoteToken?.symbol?.toUpperCase() === "SONIC" ||
                   pair.baseToken?.symbol?.toUpperCase() === "METRO" ||
                   pair.quoteToken?.symbol?.toUpperCase() === "METRO" ||
                   pair.baseToken?.symbol?.toUpperCase() === "S" ||
                   pair.quoteToken?.symbol?.toUpperCase() === "S" ||
                   pair.baseToken?.symbol?.toUpperCase() === "WSONIC" ||
                   pair.quoteToken?.symbol?.toUpperCase() === "WSONIC"));
      } else {
        isMatch = pair.chainId === dexChainId;
      }
      
      if (!isMatch) {
        console.error(`Skipping pair with wrong chain: ${pair.chainId} (expected ${dexChainId})`);
      }
      return isMatch;
    });
    console.error(`After chain filter: ${chainFilteredPairs.length} pairs remain`);
    
    // Step 2: Format pairs
    const formattedPairs = chainFilteredPairs.map(pair => {
      const formatted = formatPair(pair, chainId);
      if (!formatted) {
        console.error(`Failed to format pair: ${pair.pairAddress}`);
      }
      return formatted;
    });
    console.error(`After formatting: ${formattedPairs.filter(p => p !== null).length} pairs remain`);
    
    // Step 3: Filter by token
    const pairs = formattedPairs.filter(pair => {
      if (!pair) return false;
      
      // More lenient matching - only check if any token contains part of the query
      const baseMatch = pair.baseToken.symbol.toUpperCase().includes(query.toUpperCase());
      const quoteMatch = pair.quoteToken.symbol.toUpperCase().includes(query.toUpperCase());
      const anyMatch = baseMatch || quoteMatch;
      
      if (!anyMatch) {
        console.error(`Token mismatch for pair ${pair.pair}: base=${pair.baseToken.symbol}, quote=${pair.quoteToken.symbol}, query=${query}`);
      }
      
      return anyMatch;
    });
    
    console.error(`Found ${pairs.length} matching pairs`);
    console.log(JSON.stringify(pairs, null, 2));
    
  } catch (error) {
    console.error("Error searching pairs:", error);
    console.log("[]");
  }
}

// Parse CLI arguments
const argv = yargs(hideBin(process.argv))
  .command("search_pairs", "Search for trading pairs", {
    query: { type: "string", demandOption: true, describe: "Token name (e.g., Metro)" },
    chainId: { type: "string", default: "sonic", describe: "Chain ID (e.g., sonic)" },
  })
  .help()
  .parse();

// Execute command
if (argv._[0] === "search_pairs") {
  search(argv.query, argv.chainId);
}