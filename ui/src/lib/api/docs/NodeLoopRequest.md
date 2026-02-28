
# NodeLoopRequest

Request to set a node\'s loop mode.

## Properties

Name | Type
------------ | -------------
`guildId` | string
`loop` | boolean
`nodeId` | string

## Example

```typescript
import type { NodeLoopRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "guildId": null,
  "loop": null,
  "nodeId": null,
} satisfies NodeLoopRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as NodeLoopRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


