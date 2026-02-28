
# ChannelsResponse

List of voice channels.

## Properties

Name | Type
------------ | -------------
`channels` | [Array&lt;ChannelResponse&gt;](ChannelResponse.md)
`currentChannel` | string

## Example

```typescript
import type { ChannelsResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "channels": null,
  "currentChannel": null,
} satisfies ChannelsResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ChannelsResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


