import { 
  Box, 
  Heading, 
  Grid, 
  GridItem, 
  Card, 
  CardBody, 
  Stack, 
  FormControl, 
  FormLabel, 
  Input, 
  Select, 
  Button,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td
} from '@chakra-ui/react'

export default function Trading() {
  return (
    <Box>
      <Heading mb={6}>Trading</Heading>
      <Grid templateColumns={{ base: '1fr', lg: '2fr 1fr' }} gap={6}>
        <GridItem>
          <Card>
            <CardBody>
              <Heading size="md" mb={4}>Active Trades</Heading>
              <Table variant="simple">
                <Thead>
                  <Tr>
                    <Th>Pair</Th>
                    <Th>Type</Th>
                    <Th>Amount</Th>
                    <Th>Status</Th>
                    <Th>Action</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  <Tr>
                    <Td>ETH/USDC</Td>
                    <Td>Buy</Td>
                    <Td>1.5 ETH</Td>
                    <Td>Pending</Td>
                    <Td>
                      <Button size="sm" colorScheme="red">Cancel</Button>
                    </Td>
                  </Tr>
                </Tbody>
              </Table>
            </CardBody>
          </Card>
        </GridItem>

        <GridItem>
          <Card>
            <CardBody>
              <Heading size="md" mb={4}>New Trade</Heading>
              <Stack spacing={4}>
                <FormControl>
                  <FormLabel>Trading Pair</FormLabel>
                  <Select placeholder="Select pair">
                    <option value="eth-usdc">ETH/USDC</option>
                    <option value="btc-usdc">BTC/USDC</option>
                  </Select>
                </FormControl>
                <FormControl>
                  <FormLabel>Type</FormLabel>
                  <Select placeholder="Select type">
                    <option value="buy">Buy</option>
                    <option value="sell">Sell</option>
                  </Select>
                </FormControl>
                <FormControl>
                  <FormLabel>Amount</FormLabel>
                  <Input type="number" placeholder="Enter amount" />
                </FormControl>
                <Button colorScheme="blue">Place Trade</Button>
              </Stack>
            </CardBody>
          </Card>
        </GridItem>
      </Grid>
    </Box>
  )
}
