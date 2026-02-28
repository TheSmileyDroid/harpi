
# ActiveNodeStatus

Status of an active soundboard node.

## Properties

Name | Type
------------ | -------------
`duration` | number
`layerId` | string
`nodeId` | string
`playing` | boolean
`progress` | number
`title` | string
`url` | string
`volume` | number

## Example

```typescript
import type { ActiveNodeStatus } from ''

// TODO: Update the object below with actual values
const example = {
  "duration": null,
  "layerId": null,
  "nodeId": null,
  "playing": null,
  "progress": null,
  "title": null,
  "url": null,
  "volume": null,
} satisfies ActiveNodeStatus

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ActiveNodeStatus
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


