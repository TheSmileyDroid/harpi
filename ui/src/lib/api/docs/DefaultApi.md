# DefaultApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**deleteDeletePreset**](DefaultApi.md#deletedeletepreset) | **DELETE** /api/soundboard/presets/{preset_id} | Delete a preset. |
| [**getApiServerstatus**](DefaultApi.md#getapiserverstatus) | **GET** /api/serverstatus |  |
| [**getGetChannels**](DefaultApi.md#getgetchannels) | **GET** /api/guild/{guild_id}/channels |  |
| [**getGetGuilds**](DefaultApi.md#getgetguilds) | **GET** /api/guild |  |
| [**getGetPreset**](DefaultApi.md#getgetpreset) | **GET** /api/soundboard/presets/{preset_id} | Get a specific preset. |
| [**getGetSoundboardGraph**](DefaultApi.md#getgetsoundboardgraph) | **GET** /api/soundboard/graph/{guild_id} | Get the current soundboard graph for a guild. |
| [**getGetSoundboardStatus**](DefaultApi.md#getgetsoundboardstatus) | **GET** /api/soundboard/status/{guild_id} | Get soundboard connection and playback status. |
| [**getListPresets**](DefaultApi.md#getlistpresets) | **GET** /api/soundboard/presets | List all presets for a guild. |
| [**getMusicStatus**](DefaultApi.md#getmusicstatus) | **GET** /api/music/{guild_id}/status | Get music status for a guild. |
| [**postConnectSoundboard**](DefaultApi.md#postconnectsoundboard) | **POST** /api/soundboard/connect/{guild_id} | Connect to voice channel for soundboard playback. |
| [**postCreatePreset**](DefaultApi.md#postcreatepreset) | **POST** /api/soundboard/presets | Create a new preset. |
| [**postDisconnectSoundboard**](DefaultApi.md#postdisconnectsoundboard) | **POST** /api/soundboard/disconnect/{guild_id} | Disconnect soundboard from voice channel. |
| [**postFetchNodeMetadata**](DefaultApi.md#postfetchnodemetadata) | **POST** /api/soundboard/node/metadata | Fetch metadata for a URL without starting playback. |
| [**postMusicAdd**](DefaultApi.md#postmusicadd) | **POST** /api/music/add | Add music to queue via link. |
| [**postMusicControl**](DefaultApi.md#postmusiccontrol) | **POST** /api/music/control | Control music playback for a guild. |
| [**postSelectChannel**](DefaultApi.md#postselectchannel) | **POST** /api/guild/channel |  |
| [**postSelectGuild**](DefaultApi.md#postselectguild) | **POST** /api/guild |  |
| [**postSetNodeLoop**](DefaultApi.md#postsetnodeloop) | **POST** /api/soundboard/node/loop | Set loop for a node. |
| [**postSetNodeVolume**](DefaultApi.md#postsetnodevolume) | **POST** /api/soundboard/node/volume | Set volume for a node. |
| [**postSetSourceVolume**](DefaultApi.md#postsetsourcevolume) | **POST** /api/soundboard/source/volume | Set volume for a source. |
| [**postStartNode**](DefaultApi.md#poststartnode) | **POST** /api/soundboard/node/start | Prepare a sound source node (load but don\&#39;t play yet). |
| [**postStartSource**](DefaultApi.md#poststartsource) | **POST** /api/soundboard/source/start | Start playing a source (adds as background layer). |
| [**postStopAllSources**](DefaultApi.md#poststopallsources) | **POST** /api/soundboard/stop/{guild_id} | Stop all soundboard sources for a guild. |
| [**postStopNode**](DefaultApi.md#poststopnode) | **POST** /api/soundboard/node/stop | Stop a sound source node - stops playback and unloads. |
| [**postStopSource**](DefaultApi.md#poststopsource) | **POST** /api/soundboard/source/stop | Stop a source (removes background layer). |
| [**putUpdatePreset**](DefaultApi.md#putupdatepreset) | **PUT** /api/soundboard/presets/{preset_id} | Update an existing preset. |
| [**putUpdateSoundboardGraph**](DefaultApi.md#putupdatesoundboardgraph) | **PUT** /api/soundboard/graph/{guild_id} | Update the soundboard graph for a guild. |



## deleteDeletePreset

> StatusResponse deleteDeletePreset(presetId)

Delete a preset.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { DeleteDeletePresetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // string
    presetId: presetId_example,
  } satisfies DeleteDeletePresetRequest;

  try {
    const data = await api.deleteDeletePreset(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **presetId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**StatusResponse**](StatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getApiServerstatus

> ServerStatusModel getApiServerstatus()



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetApiServerstatusRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.getApiServerstatus();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**ServerStatusModel**](ServerStatusModel.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getGetChannels

> ChannelsResponse getGetChannels(guildId)



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetGetChannelsRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // string
    guildId: guildId_example,
  } satisfies GetGetChannelsRequest;

  try {
    const data = await api.getGetChannels(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **guildId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**ChannelsResponse**](ChannelsResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getGetGuilds

> Array&lt;GuildResponse&gt; getGetGuilds()



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetGetGuildsRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.getGetGuilds();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**Array&lt;GuildResponse&gt;**](GuildResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Built-in mutable sequence.  If no argument is given, the constructor creates a new empty list. The argument must be an iterable if specified. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getGetPreset

> PresetResponse getGetPreset(presetId)

Get a specific preset.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetGetPresetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // string
    presetId: presetId_example,
  } satisfies GetGetPresetRequest;

  try {
    const data = await api.getGetPreset(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **presetId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**PresetResponse**](PresetResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getGetSoundboardGraph

> SoundboardGraphResponse1 getGetSoundboardGraph(guildId)

Get the current soundboard graph for a guild.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetGetSoundboardGraphRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    guildId: 56,
  } satisfies GetGetSoundboardGraphRequest;

  try {
    const data = await api.getGetSoundboardGraph(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **guildId** | `number` |  | [Defaults to `undefined`] |

### Return type

[**SoundboardGraphResponse1**](SoundboardGraphResponse1.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getGetSoundboardStatus

> SoundboardStatusResponse getGetSoundboardStatus(guildId)

Get soundboard connection and playback status.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetGetSoundboardStatusRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    guildId: 56,
  } satisfies GetGetSoundboardStatusRequest;

  try {
    const data = await api.getGetSoundboardStatus(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **guildId** | `number` |  | [Defaults to `undefined`] |

### Return type

[**SoundboardStatusResponse**](SoundboardStatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getListPresets

> Array&lt;PresetListResponse&gt; getListPresets()

List all presets for a guild.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetListPresetsRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  try {
    const data = await api.getListPresets();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**Array&lt;PresetListResponse&gt;**](PresetListResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Built-in mutable sequence.  If no argument is given, the constructor creates a new empty list. The argument must be an iterable if specified. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getMusicStatus

> MusicStatusResponse getMusicStatus(guildId)

Get music status for a guild.

 Query params:     guild_id: The guild ID to get status for.  Returns:     JSON with music data or error.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { GetMusicStatusRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // string
    guildId: guildId_example,
  } satisfies GetMusicStatusRequest;

  try {
    const data = await api.getMusicStatus(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **guildId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**MusicStatusResponse**](MusicStatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postConnectSoundboard

> ConnectionResponse postConnectSoundboard(guildId, connectSoundboardRequest)

Connect to voice channel for soundboard playback.

 Body:     channel_id: The voice channel ID to connect to.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostConnectSoundboardRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    guildId: 56,
    // ConnectSoundboardRequest (optional)
    connectSoundboardRequest: ...,
  } satisfies PostConnectSoundboardRequest;

  try {
    const data = await api.postConnectSoundboard(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **guildId** | `number` |  | [Defaults to `undefined`] |
| **connectSoundboardRequest** | [ConnectSoundboardRequest](ConnectSoundboardRequest.md) |  | [Optional] |

### Return type

[**ConnectionResponse**](ConnectionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postCreatePreset

> PresetResponse postCreatePreset(createPresetRequest)

Create a new preset.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostCreatePresetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // CreatePresetRequest (optional)
    createPresetRequest: ...,
  } satisfies PostCreatePresetRequest;

  try {
    const data = await api.postCreatePreset(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **createPresetRequest** | [CreatePresetRequest](CreatePresetRequest.md) |  | [Optional] |

### Return type

[**PresetResponse**](PresetResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postDisconnectSoundboard

> postDisconnectSoundboard(guildId)

Disconnect soundboard from voice channel.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostDisconnectSoundboardRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    guildId: 56,
  } satisfies PostDisconnectSoundboardRequest;

  try {
    const data = await api.postDisconnectSoundboard(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **guildId** | `number` |  | [Defaults to `undefined`] |

### Return type

`void` (Empty response body)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: Not defined


[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postFetchNodeMetadata

> MetadataResponse postFetchNodeMetadata(metadataRequest)

Fetch metadata for a URL without starting playback.

 Body:     url: The audio URL (YouTube, etc).

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostFetchNodeMetadataRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // MetadataRequest (optional)
    metadataRequest: ...,
  } satisfies PostFetchNodeMetadataRequest;

  try {
    const data = await api.postFetchNodeMetadata(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **metadataRequest** | [MetadataRequest](MetadataRequest.md) |  | [Optional] |

### Return type

[**MetadataResponse**](MetadataResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postMusicAdd

> MusicAddResponse postMusicAdd(musicAddRequest)

Add music to queue via link.

 Body:     guild_id: The guild ID.     channel_id: The voice channel ID to connect to.     link: The music URL (YouTube, etc).     type: (Optional) \&#39;queue\&#39; (default) or \&#39;layer\&#39;.  Returns:     JSON with status or error.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostMusicAddRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // MusicAddRequest (optional)
    musicAddRequest: ...,
  } satisfies PostMusicAddRequest;

  try {
    const data = await api.postMusicAdd(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **musicAddRequest** | [MusicAddRequest](MusicAddRequest.md) |  | [Optional] |

### Return type

[**MusicAddResponse**](MusicAddResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postMusicControl

> MusicControlResponse postMusicControl(musicControlRequest)

Control music playback for a guild.

 Body:     guild_id: The guild ID.     action: One of \&#39;stop\&#39;, \&#39;skip\&#39;, \&#39;pause\&#39;, \&#39;resume\&#39;, \&#39;loop\&#39;.     mode: (Optional) Loop mode for \&#39;loop\&#39; action.  Returns:     JSON with status or error.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostMusicControlRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // MusicControlRequest (optional)
    musicControlRequest: ...,
  } satisfies PostMusicControlRequest;

  try {
    const data = await api.postMusicControl(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **musicControlRequest** | [MusicControlRequest](MusicControlRequest.md) |  | [Optional] |

### Return type

[**MusicControlResponse**](MusicControlResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postSelectChannel

> ChannelSelectResponse postSelectChannel(selectChannelRequest)



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostSelectChannelRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // SelectChannelRequest (optional)
    selectChannelRequest: ...,
  } satisfies PostSelectChannelRequest;

  try {
    const data = await api.postSelectChannel(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **selectChannelRequest** | [SelectChannelRequest](SelectChannelRequest.md) |  | [Optional] |

### Return type

[**ChannelSelectResponse**](ChannelSelectResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postSelectGuild

> GuildSelectResponse postSelectGuild(selectGuildRequest)



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostSelectGuildRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // SelectGuildRequest (optional)
    selectGuildRequest: ...,
  } satisfies PostSelectGuildRequest;

  try {
    const data = await api.postSelectGuild(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **selectGuildRequest** | [SelectGuildRequest](SelectGuildRequest.md) |  | [Optional] |

### Return type

[**GuildSelectResponse**](GuildSelectResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postSetNodeLoop

> SourceActionResponse postSetNodeLoop(nodeLoopRequest)

Set loop for a node.

 Body:     guild_id: The guild ID.     node_id: The node identifier.     loop: Whether to loop the audio.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostSetNodeLoopRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // NodeLoopRequest (optional)
    nodeLoopRequest: ...,
  } satisfies PostSetNodeLoopRequest;

  try {
    const data = await api.postSetNodeLoop(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **nodeLoopRequest** | [NodeLoopRequest](NodeLoopRequest.md) |  | [Optional] |

### Return type

[**SourceActionResponse**](SourceActionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postSetNodeVolume

> SourceVolumeResponse postSetNodeVolume(nodeVolumeRequest)

Set volume for a node.

 Body:     guild_id: The guild ID.     node_id: The node identifier.     volume: Volume level (0-200).

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostSetNodeVolumeRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // NodeVolumeRequest (optional)
    nodeVolumeRequest: ...,
  } satisfies PostSetNodeVolumeRequest;

  try {
    const data = await api.postSetNodeVolume(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **nodeVolumeRequest** | [NodeVolumeRequest](NodeVolumeRequest.md) |  | [Optional] |

### Return type

[**SourceVolumeResponse**](SourceVolumeResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postSetSourceVolume

> SourceVolumeResponse postSetSourceVolume(sourceVolumeRequest)

Set volume for a source.

 Body:     guild_id: The guild ID.     node_id: The node identifier.     volume: Volume level (0-200).

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostSetSourceVolumeRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // SourceVolumeRequest (optional)
    sourceVolumeRequest: ...,
  } satisfies PostSetSourceVolumeRequest;

  try {
    const data = await api.postSetSourceVolume(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **sourceVolumeRequest** | [SourceVolumeRequest](SourceVolumeRequest.md) |  | [Optional] |

### Return type

[**SourceVolumeResponse**](SourceVolumeResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postStartNode

> SourceActionResponse postStartNode(startNodeRequest)

Prepare a sound source node (load but don\&#39;t play yet).

 Body:     guild_id: The guild ID.     node_id: Unique node identifier for this source.     url: The audio URL.     volume: Initial volume (0-200, default 100).     loop: Whether to loop the audio (default false).

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostStartNodeRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // StartNodeRequest (optional)
    startNodeRequest: ...,
  } satisfies PostStartNodeRequest;

  try {
    const data = await api.postStartNode(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **startNodeRequest** | [StartNodeRequest](StartNodeRequest.md) |  | [Optional] |

### Return type

[**SourceActionResponse**](SourceActionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postStartSource

> SourceActionResponse postStartSource(startSourceRequest)

Start playing a source (adds as background layer).

 Body:     guild_id: The guild ID.     channel_id: The voice channel ID (required if not connected).     node_id: Unique node identifier for this source.     url: The audio URL.     volume: Initial volume (0-200, default 100).

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostStartSourceRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // StartSourceRequest (optional)
    startSourceRequest: ...,
  } satisfies PostStartSourceRequest;

  try {
    const data = await api.postStartSource(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **startSourceRequest** | [StartSourceRequest](StartSourceRequest.md) |  | [Optional] |

### Return type

[**SourceActionResponse**](SourceActionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postStopAllSources

> StatusResponse postStopAllSources(guildId)

Stop all soundboard sources for a guild.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostStopAllSourcesRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    guildId: 56,
  } satisfies PostStopAllSourcesRequest;

  try {
    const data = await api.postStopAllSources(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **guildId** | `number` |  | [Defaults to `undefined`] |

### Return type

[**StatusResponse**](StatusResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postStopNode

> SourceActionResponse postStopNode(stopNodeRequest)

Stop a sound source node - stops playback and unloads.

 Body:     guild_id: The guild ID.     node_id: The node identifier to stop.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostStopNodeRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // StopNodeRequest (optional)
    stopNodeRequest: ...,
  } satisfies PostStopNodeRequest;

  try {
    const data = await api.postStopNode(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **stopNodeRequest** | [StopNodeRequest](StopNodeRequest.md) |  | [Optional] |

### Return type

[**SourceActionResponse**](SourceActionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postStopSource

> SourceActionResponse postStopSource(stopSourceRequest)

Stop a source (removes background layer).

 Body:     guild_id: The guild ID.     node_id: The node identifier to stop.

### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostStopSourceRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // StopSourceRequest (optional)
    stopSourceRequest: ...,
  } satisfies PostStopSourceRequest;

  try {
    const data = await api.postStopSource(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **stopSourceRequest** | [StopSourceRequest](StopSourceRequest.md) |  | [Optional] |

### Return type

[**SourceActionResponse**](SourceActionResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## putUpdatePreset

> PresetResponse putUpdatePreset(presetId, updatePresetRequest)

Update an existing preset.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PutUpdatePresetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // string
    presetId: presetId_example,
    // UpdatePresetRequest (optional)
    updatePresetRequest: ...,
  } satisfies PutUpdatePresetRequest;

  try {
    const data = await api.putUpdatePreset(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **presetId** | `string` |  | [Defaults to `undefined`] |
| **updatePresetRequest** | [UpdatePresetRequest](UpdatePresetRequest.md) |  | [Optional] |

### Return type

[**PresetResponse**](PresetResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## putUpdateSoundboardGraph

> SoundboardGraphResponse2 putUpdateSoundboardGraph(guildId, updateGraphRequest)

Update the soundboard graph for a guild.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PutUpdateSoundboardGraphRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // number
    guildId: 56,
    // UpdateGraphRequest (optional)
    updateGraphRequest: ...,
  } satisfies PutUpdateSoundboardGraphRequest;

  try {
    const data = await api.putUpdateSoundboardGraph(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **guildId** | `number` |  | [Defaults to `undefined`] |
| **updateGraphRequest** | [UpdateGraphRequest](UpdateGraphRequest.md) |  | [Optional] |

### Return type

[**SoundboardGraphResponse2**](SoundboardGraphResponse2.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** |  |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

