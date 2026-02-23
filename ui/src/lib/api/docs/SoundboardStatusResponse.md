
# SoundboardStatusResponse


## Properties

Name | Type
------------ | -------------
`activeNodes` | [Array&lt;ActiveNodeStatus&gt;](ActiveNodeStatus.md)
`channelId` | number
`channelName` | string
`connected` | boolean
`graph` | [SoundboardGraphResponse](SoundboardGraphResponse.md)

## Example

```typescript
import type { SoundboardStatusResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "activeNodes": null,
  "channelId": null,
  "channelName": null,
  "connected": null,
  "graph": null,
} satisfies SoundboardStatusResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as SoundboardStatusResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


