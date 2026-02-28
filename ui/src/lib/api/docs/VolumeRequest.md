
# VolumeRequest

Request to change volume.

## Properties

Name | Type
------------ | -------------
`guildId` | string
`volume` | number

## Example

```typescript
import type { VolumeRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "guildId": null,
  "volume": null,
} satisfies VolumeRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as VolumeRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


