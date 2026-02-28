
# GuildSelectResponse

Response after selecting a guild.

## Properties

Name | Type
------------ | -------------
`error` | string
`guild` | [GuildResponse](GuildResponse.md)
`success` | boolean

## Example

```typescript
import type { GuildSelectResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "error": null,
  "guild": null,
  "success": null,
} satisfies GuildSelectResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as GuildSelectResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


