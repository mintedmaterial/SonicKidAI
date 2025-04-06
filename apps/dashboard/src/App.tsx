import { useEffect } from 'react'
import { BrowserRouter } from 'react-router-dom'
import { ThirdwebProvider } from '@thirdweb-dev/react'
import { Sepolia } from '@thirdweb-dev/chains'
import { ChakraProvider } from '@chakra-ui/react'
import { Provider as UrqlProvider } from 'urql'
import { client as graphqlClient } from './utils/subgraph'
import { WebApp, isTelegramWebApp } from './utils/telegram'
import theme from './theme'
import Router from './Router'

export default function App() {
  useEffect(() => {
    // Initialize Telegram Web App if in Telegram context
    if (isTelegramWebApp()) {
      WebApp?.ready()
      WebApp?.expand()
    }
  }, [])

  return (
    <ChakraProvider theme={theme}>
      <UrqlProvider value={graphqlClient}>
        <ThirdwebProvider
          activeChain={Sepolia}
          clientId={import.meta.env.VITE_THIRDWEB_CLIENT_ID}
        >
          <BrowserRouter>
            <Router />
          </BrowserRouter>
        </ThirdwebProvider>
      </UrqlProvider>
    </ChakraProvider>
  )
}
