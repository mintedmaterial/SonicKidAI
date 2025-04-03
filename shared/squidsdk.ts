import { Squid } from "@0xsquid/sdk";
import { ethers } from "ethers";

// Initialize Squid SDK with proper configuration
export const initSquidSdk = () => {
  const squidConfig = {
    baseUrl: process.env.SQUID_SDK_URL || "https://apiplus.squidrouter.com",
    integratorId: process.env.SQUID_INTEGRATOR_ID || "",  // Default to empty string
  };

  return new Squid(squidConfig);
};

// Convert token amount to Wei based on decimals
export const convertToWei = (amount: string | number, decimals: number = 18): string => {
  return ethers.parseUnits(amount.toString(), decimals).toString();
};

// Interface for cross-chain swap parameters
export interface CrossChainSwapParams {
  fromChain: string;
  toChain: string;
  fromToken: string;
  toToken: string;
  amount: string;
  fromAddress: string;
  toAddress: string;
}

// Execute cross-chain swap
export const executeCrossChainSwap = async (params: CrossChainSwapParams) => {
  try {
    const squid = initSquidSdk();
    await squid.init();

    // Get signer using private key
    const provider = new ethers.JsonRpcProvider(squid.chains.find(c => c.chainId === params.fromChain)?.rpc);
    const signer = new ethers.Wallet(process.env.SQUID_EVM_PRIVATE_KEY!, provider);

    const swapParams = {
      fromAddress: params.fromAddress,
      fromChain: parseInt(params.fromChain),
      fromToken: params.fromToken,
      fromAmount: convertToWei(params.amount),
      toChain: parseInt(params.toChain),
      toToken: params.toToken,
      toAddress: params.toAddress,
      slippage: 1, // 1% slippage
      enableForecall: true,
      quoteOnly: false
    };

    // Get route
    const { route } = await squid.getRoute(swapParams);

    // Execute the swap
    const tx = await squid.executeRoute({
      signer,
      route,
    });

    const txReceipt = await tx.wait();

    return {
      success: true,
      transactionHash: txReceipt.hash,
      fromChain: params.fromChain,
      toChain: params.toChain,
      amount: params.amount
    };

  } catch (error) {
    console.error("Cross-chain swap error:", error);
    return {
      success: false,
      error: error instanceof Error ? error.message : String(error)
    };
  }
};