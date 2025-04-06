import { 
  Box, 
  Heading, 
  SimpleGrid, 
  Card, 
  CardBody, 
  Text, 
  Button, 
  VStack,
  HStack,
  Icon,
  Divider,
  Avatar
} from '@chakra-ui/react'

export default function Social() {
  return (
    <Box>
      <Heading mb={6}>Social Media</Heading>
      <SimpleGrid columns={{ base: 1, lg: 2 }} gap={6}>
        <Card>
          <CardBody>
            <Heading size="md" mb={4}>Twitter Feed</Heading>
            <VStack spacing={4} align="stretch">
              <Box p={4} borderWidth={1} borderRadius="lg">
                <HStack spacing={4} mb={2}>
                  <Avatar size="sm" name="User" />
                  <Text fontWeight="bold">@user</Text>
                </HStack>
                <Text mb={2}>
                  Just made my first trade on SonicKid! Amazing experience 🚀
                </Text>
                <HStack spacing={4} color="gray.500">
                  <Text>❤️ 42</Text>
                  <Text>🔄 12</Text>
                </HStack>
              </Box>
              <Button variant="outline">Load More</Button>
            </VStack>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Heading size="md" mb={4}>Discord Activity</Heading>
            <VStack spacing={4} align="stretch">
              <Box p={4} borderWidth={1} borderRadius="lg">
                <HStack spacing={4} mb={2}>
                  <Avatar size="sm" name="Discord User" />
                  <Text fontWeight="bold">Discord User</Text>
                </HStack>
                <Text mb={2}>
                  New announcement in #trading-signals
                </Text>
                <Text color="gray.500">2 minutes ago</Text>
              </Box>
              <Divider />
              <Button colorScheme="blue">Open Discord</Button>
            </VStack>
          </CardBody>
        </Card>
      </SimpleGrid>
    </Box>
  )
}
