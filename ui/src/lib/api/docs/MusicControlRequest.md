
# MusicControlRequest

Legacy control request (deprecated).

## Properties

Name | Type
------------ | -------------
`action` | string
`guildId` | string
`layerId` | string
`mode` | string
`volume` | number

## Example

```typescript
import type { MusicControlRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "action": null,
  "guildId": null,
  "layerId": null,
  "mode": null,
  "volume": null,
} satisfies MusicControlRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MusicControlRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


