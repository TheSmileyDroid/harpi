
# MusicStatusResponse


## Properties

Name | Type
------------ | -------------
`currentMusic` | [MusicTrackResponse](MusicTrackResponse.md)
`isPaused` | boolean
`isPlaying` | boolean
`layers` | [Array&lt;MusicLayerResponse&gt;](MusicLayerResponse.md)
`loopMode` | string
`progress` | number
`queue` | [Array&lt;QueueItemResponse&gt;](QueueItemResponse.md)
`volume` | number

## Example

```typescript
import type { MusicStatusResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "currentMusic": null,
  "isPaused": null,
  "isPlaying": null,
  "layers": null,
  "loopMode": null,
  "progress": null,
  "queue": null,
  "volume": null,
} satisfies MusicStatusResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as MusicStatusResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


