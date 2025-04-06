import { 
  Box, 
  Heading, 
  SimpleGrid, 
  Card, 
  CardBody, 
  Text, 
  Stat,
  StatLabel,
  StatNumber,
  StatHelpText,
  StatArrow,
  Stack
} from '@chakra-ui/react'

export default function Analytics() {
  return (
    <Box>
      <Heading mb={6}>Analytics</Heading>
      <SimpleGrid columns={{ base: 1, md: 2, lg: 4 }} gap={6} mb={8}>
        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Total Volume</StatLabel>
              <StatNumber>$1.2M</StatNumber>
              <StatHelpText>
                <StatArrow type="increase" />
                23.36%
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Active Users</StatLabel>
              <StatNumber>1,234</StatNumber>
              <StatHelpText>
                <StatArrow type="increase" />
                12.5%
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Success Rate</StatLabel>
              <StatNumber>89%</StatNumber>
              <StatHelpText>
                <StatArrow type="increase" />
                5.2%
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Stat>
              <StatLabel>Average ROI</StatLabel>
              <StatNumber>15.4%</StatNumber>
              <StatHelpText>
                <StatArrow type="decrease" />
                2.1%
              </StatHelpText>
            </Stat>
          </CardBody>
        </Card>
      </SimpleGrid>

      <SimpleGrid columns={{ base: 1, lg: 2 }} gap={6}>
        <Card>
          <CardBody>
            <Heading size="md" mb={4}>Trading Performance</Heading>
            <Text color="gray.500">Chart will be implemented here</Text>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <Heading size="md" mb={4}>User Activity</Heading>
            <Text color="gray.500">Chart will be implemented here</Text>
          </CardBody>
        </Card>
      </SimpleGrid>
    </Box>
  )
}
