import { createThirdwebClient } from "thirdweb";

// Initialize the ThirdWeb client with configuration
export const client = createThirdwebClient({
  clientId: import.meta.env.VITE_THIRDWEB_CLIENT_ID,
  
  // Configure app metadata
  appMetadata: {
    name: "SonicKid Dashboard",
    url: import.meta.env.VITE_PUBLIC_URL || "https://sonickid.io",
  },
});
