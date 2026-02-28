# DefaultApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getApiServerstatus**](DefaultApi.md#getapiserverstatus) | **GET** /api/serverstatus |  |
| [**getGetChannels**](DefaultApi.md#getgetchannels) | **GET** /api/guild/{guild_id}/channels |  |
| [**getGetGuilds**](DefaultApi.md#getgetguilds) | **GET** /api/guild |  |
| [**getMusicStatus**](DefaultApi.md#getmusicstatus) | **GET** /api/music/{guild_id}/status | Get music status for a guild. |
| [**postMusicAdd**](DefaultApi.md#postmusicadd) | **POST** /api/music/add | Add music to queue via link. |
| [**postMusicControl**](DefaultApi.md#postmusiccontrol) | **POST** /api/music/control | Control music playback for a guild. |
| [**postMusicLayerClean**](DefaultApi.md#postmusiclayerclean) | **POST** /api/music/layer/clean | Remove all background audio layers. |
| [**postMusicLayerRemove**](DefaultApi.md#postmusiclayerremove) | **POST** /api/music/layer/remove | Remove a background audio layer. |
| [**postMusicLayerVolume**](DefaultApi.md#postmusiclayervolume) | **POST** /api/music/layer/volume | Set volume for a specific background audio layer. |
| [**postMusicLoop**](DefaultApi.md#postmusicloop) | **POST** /api/music/loop | Set the loop mode (off, track, queue). |
| [**postMusicPause**](DefaultApi.md#postmusicpause) | **POST** /api/music/pause | Pause music playback. |
| [**postMusicResume**](DefaultApi.md#postmusicresume) | **POST** /api/music/resume | Resume music playback. |
| [**postMusicSkip**](DefaultApi.md#postmusicskip) | **POST** /api/music/skip | Skip to the next track in the queue. |
| [**postMusicStop**](DefaultApi.md#postmusicstop) | **POST** /api/music/stop | Stop music playback for a guild. |
| [**postMusicVolume**](DefaultApi.md#postmusicvolume) | **POST** /api/music/volume | Set the main playback volume. |
| [**postSelectChannel**](DefaultApi.md#postselectchannel) | **POST** /api/guild/channel |  |
| [**postSelectGuild**](DefaultApi.md#postselectguild) | **POST** /api/guild |  |



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
| **200** | List of voice channels. |  -  |

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


## getMusicStatus

> MusicStatusResponse getMusicStatus(guildId)

Get music status for a guild.

 Query params:     guild_id: The guild ID to get status for.

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
| **200** | Full music playback status for a guild. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postMusicAdd

> MusicAddResponse postMusicAdd(musicAddRequest)

Add music to queue via link.

 Body:     guild_id: The guild ID.     channel_id: The voice channel ID to connect to.     link: The music URL (YouTube, etc).     type: (Optional) \&#39;queue\&#39; (default) or \&#39;layer\&#39;.

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
| **200** | Response after adding music. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postMusicControl

> MusicControlResponse postMusicControl(musicControlRequest)

Control music playback for a guild.

 .. deprecated::     Use the individual endpoints instead (e.g. POST /api/music/stop).  Body:     guild_id: The guild ID.     action: One of \&#39;stop\&#39;, \&#39;skip\&#39;, \&#39;pause\&#39;, \&#39;resume\&#39;, \&#39;loop\&#39;,             \&#39;remove_layer\&#39;, \&#39;clean_layers\&#39;, \&#39;set_volume\&#39;, \&#39;set_layer_volume\&#39;.     mode: (Optional) Loop mode for \&#39;loop\&#39; action.     layer_id: (Optional) Layer ID for layer actions.     volume: (Optional) Volume level.

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
| **200** | Response for a music control action. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postMusicLayerClean

> MusicControlResponse postMusicLayerClean(guildRequest)

Remove all background audio layers.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostMusicLayerCleanRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // GuildRequest (optional)
    guildRequest: ...,
  } satisfies PostMusicLayerCleanRequest;

  try {
    const data = await api.postMusicLayerClean(body);
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
| **guildRequest** | [GuildRequest](GuildRequest.md) |  | [Optional] |

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
| **200** | Response for a music control action. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postMusicLayerRemove

> MusicControlResponse postMusicLayerRemove(layerRemoveRequest)

Remove a background audio layer.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostMusicLayerRemoveRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // LayerRemoveRequest (optional)
    layerRemoveRequest: ...,
  } satisfies PostMusicLayerRemoveRequest;

  try {
    const data = await api.postMusicLayerRemove(body);
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
| **layerRemoveRequest** | [LayerRemoveRequest](LayerRemoveRequest.md) |  | [Optional] |

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
| **200** | Response for a music control action. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postMusicLayerVolume

> MusicControlResponse postMusicLayerVolume(layerVolumeRequest)

Set volume for a specific background audio layer.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostMusicLayerVolumeRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // LayerVolumeRequest (optional)
    layerVolumeRequest: ...,
  } satisfies PostMusicLayerVolumeRequest;

  try {
    const data = await api.postMusicLayerVolume(body);
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
| **layerVolumeRequest** | [LayerVolumeRequest](LayerVolumeRequest.md) |  | [Optional] |

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
| **200** | Response for a music control action. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postMusicLoop

> MusicControlResponse postMusicLoop(loopRequest)

Set the loop mode (off, track, queue).



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostMusicLoopRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // LoopRequest (optional)
    loopRequest: ...,
  } satisfies PostMusicLoopRequest;

  try {
    const data = await api.postMusicLoop(body);
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
| **loopRequest** | [LoopRequest](LoopRequest.md) |  | [Optional] |

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
| **200** | Response for a music control action. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postMusicPause

> MusicControlResponse postMusicPause(guildRequest)

Pause music playback.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostMusicPauseRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // GuildRequest (optional)
    guildRequest: ...,
  } satisfies PostMusicPauseRequest;

  try {
    const data = await api.postMusicPause(body);
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
| **guildRequest** | [GuildRequest](GuildRequest.md) |  | [Optional] |

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
| **200** | Response for a music control action. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postMusicResume

> MusicControlResponse postMusicResume(guildRequest)

Resume music playback.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostMusicResumeRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // GuildRequest (optional)
    guildRequest: ...,
  } satisfies PostMusicResumeRequest;

  try {
    const data = await api.postMusicResume(body);
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
| **guildRequest** | [GuildRequest](GuildRequest.md) |  | [Optional] |

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
| **200** | Response for a music control action. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postMusicSkip

> MusicControlResponse postMusicSkip(guildRequest)

Skip to the next track in the queue.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostMusicSkipRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // GuildRequest (optional)
    guildRequest: ...,
  } satisfies PostMusicSkipRequest;

  try {
    const data = await api.postMusicSkip(body);
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
| **guildRequest** | [GuildRequest](GuildRequest.md) |  | [Optional] |

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
| **200** | Response for a music control action. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postMusicStop

> MusicControlResponse postMusicStop(guildRequest)

Stop music playback for a guild.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostMusicStopRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // GuildRequest (optional)
    guildRequest: ...,
  } satisfies PostMusicStopRequest;

  try {
    const data = await api.postMusicStop(body);
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
| **guildRequest** | [GuildRequest](GuildRequest.md) |  | [Optional] |

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
| **200** | Response for a music control action. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## postMusicVolume

> MusicControlResponse postMusicVolume(volumeRequest)

Set the main playback volume.



### Example

```ts
import {
  Configuration,
  DefaultApi,
} from '';
import type { PostMusicVolumeRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new DefaultApi();

  const body = {
    // VolumeRequest (optional)
    volumeRequest: ...,
  } satisfies PostMusicVolumeRequest;

  try {
    const data = await api.postMusicVolume(body);
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
| **volumeRequest** | [VolumeRequest](VolumeRequest.md) |  | [Optional] |

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
| **200** | Response for a music control action. |  -  |

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
| **200** | Response after selecting a channel. |  -  |

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
| **200** | Response after selecting a guild. |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

