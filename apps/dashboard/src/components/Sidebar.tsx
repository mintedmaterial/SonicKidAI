import { Box, VStack, Link, Text, Icon, useColorMode } from '@chakra-ui/react'
import { Link as RouterLink } from 'react-router-dom'

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/', icon: '📊' },
  { label: 'NFTs', path: '/nfts', icon: '🖼️' },
  { label: 'Trading', path: '/trading', icon: '📈' },
  { label: 'Social', path: '/social', icon: '💬' },
  { label: 'Analytics', path: '/analytics', icon: '📉' },
  { label: 'Settings', path: '/settings', icon: '⚙️' },
]

export default function Sidebar() {
  const { colorMode } = useColorMode()

  return (
    <Box
      as="nav"
      h="100vh"
      w="240px"
      borderRight="1px"
      borderColor="gray.200"
      bg={colorMode === 'light' ? 'white' : 'gray.800'}
      py={8}
      position="sticky"
      top={0}
    >
      <VStack spacing={2} align="stretch">
        {NAV_ITEMS.map((item) => (
          <Link
            key={item.path}
            as={RouterLink}
            to={item.path}
            px={6}
            py={3}
            display="flex"
            alignItems="center"
            _hover={{
              bg: colorMode === 'light' ? 'gray.100' : 'gray.700',
            }}
          >
            <Text fontSize="lg" mr={3}>
              {item.icon}
            </Text>
            <Text>{item.label}</Text>
          </Link>
        ))}
      </VStack>
    </Box>
  )
}
