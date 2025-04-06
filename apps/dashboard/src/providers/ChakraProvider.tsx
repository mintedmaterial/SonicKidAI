import { ChakraProvider as ChakraUIProvider, ColorModeScript } from '@chakra-ui/react'
import { ReactNode } from 'react'
import theme from '../theme'

interface ChakraProviderProps {
  children: ReactNode
}

export function ChakraProvider({ children }: ChakraProviderProps) {
  return (
    <ChakraUIProvider theme={theme}>
      <ColorModeScript initialColorMode={theme.config.initialColorMode} />
      {children}
    </ChakraUIProvider>
  )
}
