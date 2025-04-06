import { Box, Container, Flex } from '@chakra-ui/react'
import { ReactNode } from 'react'
import Sidebar from '../components/Sidebar'
import Header from '../components/Header'

interface MainLayoutProps {
  children: ReactNode
}

export default function MainLayout({ children }: MainLayoutProps) {
  return (
    <Flex minH="100vh">
      <Sidebar />
      <Box flex="1">
        <Header />
        <Container maxW="container.xl" py={8}>
          {children}
        </Container>
      </Box>
    </Flex>
  )
}
