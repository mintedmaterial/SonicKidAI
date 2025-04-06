import { Box, Heading, SimpleGrid, Stat, StatLabel, StatNumber, StatHelpText, Card, CardBody } from '@chakra-ui/react'

export default function Dashboard() {
  return (
    <Box>
      <Heading mb={6}>Dashboard</Heading>
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} spacing={6}>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total NFTs</StatLabel>
              <StatNumber>0</StatNumber>
              <StatHelpText>In your collection</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Active Trades</StatLabel>
              <StatNumber>0</StatNumber>
              <StatHelpText>Last 24h</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Social Engagement</StatLabel>
              <StatNumber>0</StatNumber>
              <StatHelpText>Interactions</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Analytics Score</StatLabel>
              <StatNumber>0</StatNumber>
              <StatHelpText>Performance</StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </SimpleGrid>
    </Box>
  )
}
