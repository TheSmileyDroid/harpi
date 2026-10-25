# 06: SSRF URL policy and yt-dlp wiring

**What to build:** A viewer can queue YouTube links, and the app rejects non-YouTube URLs, private addresses, and redirects to private addresses before yt-dlp fetches them.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] A pure policy seam takes a URL and a resolver and returns allow or deny with a reason.
- [ ] Public mode allows YouTube and its CDN and rejects other hosts.
- [ ] The policy rejects loopback, RFC1918, link-local, multicast, IPv6 loopback, and the metadata address.
- [ ] The policy rejects hostnames that resolve to a private address, including wildcard DNS services.
- [ ] The policy rejects a redirect that ends at a private address.
- [ ] yt-dlp's `allowed_extractors` is restricted, and playlists are limited to one item.
- [ ] The API answers 400 in the existing error envelope for a rejected URL.
- [ ] Tests cover allowed YouTube, non-YouTube, private resolution, metadata, and redirect cases.
- [ ] Demo: an internal URL is blocked, and a YouTube URL still plays.
