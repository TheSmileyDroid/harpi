
# ServerStatusModel


## Properties

Name | Type
------------ | -------------
`cpu` | number
`memoryAvailable` | number
`memoryFree` | number
`memoryPercent` | number
`memoryTotal` | number
`memoryUsed` | number

## Example

```typescript
import type { ServerStatusModel } from ''

// TODO: Update the object below with actual values
const example = {
  "cpu": null,
  "memoryAvailable": null,
  "memoryFree": null,
  "memoryPercent": null,
  "memoryTotal": null,
  "memoryUsed": null,
} satisfies ServerStatusModel

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ServerStatusModel
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


