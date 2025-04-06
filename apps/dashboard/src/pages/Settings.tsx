import { 
  Box, 
  Heading, 
  Card, 
  CardBody, 
  Stack,
  FormControl,
  FormLabel,
  Input,
  Switch,
  Button,
  Divider,
  Text,
  VStack,
  HStack
} from '@chakra-ui/react'

export default function Settings() {
  return (
    <Box>
      <Heading mb={6}>Settings</Heading>
      <Stack spacing={6}>
        <Card>
          <CardBody>
            <VStack spacing={4} align="stretch">
              <Heading size="md">Profile Settings</Heading>
              <FormControl>
                <FormLabel>Display Name</FormLabel>
                <Input placeholder="Enter your display name" />
              </FormControl>
              <FormControl>
                <FormLabel>Email</FormLabel>
                <Input type="email" placeholder="Enter your email" />
              </FormControl>
              <Button colorScheme="blue">Save Profile</Button>
            </VStack>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <VStack spacing={4} align="stretch">
              <Heading size="md">Trading Settings</Heading>
              <FormControl display="flex" alignItems="center">
                <FormLabel mb="0">Enable Auto-Trading</FormLabel>
                <Switch />
              </FormControl>
              <FormControl display="flex" alignItems="center">
                <FormLabel mb="0">Trading Notifications</FormLabel>
                <Switch defaultChecked />
              </FormControl>
              <FormControl>
                <FormLabel>Max Trade Amount</FormLabel>
                <Input type="number" placeholder="Enter max trade amount" />
              </FormControl>
              <Button colorScheme="blue">Save Trading Settings</Button>
            </VStack>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <VStack spacing={4} align="stretch">
              <Heading size="md">Social Integration</Heading>
              <HStack justify="space-between">
                <Text>Twitter</Text>
                <Button size="sm">Connect</Button>
              </HStack>
              <HStack justify="space-between">
                <Text>Discord</Text>
                <Button size="sm">Connect</Button>
              </HStack>
              <HStack justify="space-between">
                <Text>Telegram</Text>
                <Button size="sm">Connect</Button>
              </HStack>
            </VStack>
          </CardBody>
        </Card>
      </Stack>
    </Box>
  )
}
