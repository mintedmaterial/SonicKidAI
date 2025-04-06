import { Box, Heading, SimpleGrid, Card, CardBody, Image, Text, Button } from '@chakra-ui/react'

export default function NFTs() {
  return (
    <Box>
      <Heading mb={6}>NFT Collection</Heading>
      <SimpleGrid columns={{ base: 1, md: 2, lg: 3 }} gap={6}>
        <Card>
          <CardBody>
            <Image
              src="https://via.placeholder.com/300"
              alt="NFT placeholder"
              borderRadius="lg"
              mb={4}
            />
            <Text fontSize="xl" fontWeight="bold" mb={2}>
              NFT #1
            </Text>
            <Text color="gray.500" mb={4}>
              Description of the NFT goes here
            </Text>
            <Button width="full">View Details</Button>
          </CardBody>
        </Card>
        {/* Add more NFT cards here */}
      </SimpleGrid>
    </Box>
  )
}
