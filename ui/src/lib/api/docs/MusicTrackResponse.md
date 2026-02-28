
# MusicTrackResponse

Current track information.

## Properties

Name | Type
------------ | -------------
`duration` | number
`title` | string
`url` | string

## Example

```typescript
import type { MusicTrackResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "duration": null,
  "title": null,
  "url": null,
} satisfies MusicTrackResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MusicTrackResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


