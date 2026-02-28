
# CreatePresetRequest

Request to create a preset.

## Properties

Name | Type
------------ | -------------
`edges` | Array&lt;{ [key: string]: any; }&gt;
`guildId` | number
`name` | string
`nodes` | Array&lt;{ [key: string]: any; }&gt;

## Example

```typescript
import type { CreatePresetRequest } from ''

// TODO: Update the object below with actual values
const example = {
  "edges": null,
  "guildId": null,
  "name": null,
  "nodes": null,
} satisfies CreatePresetRequest

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as CreatePresetRequest
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


