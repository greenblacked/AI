# Association files

Annotated examples of the two files and the Android manifest filter, and the server
behaviour that breaks them. Replace the example identifiers; everything else is the shape
the platforms expect.

## Contents

- apple-app-site-association
- assetlinks.json
- The Android intent filter
- Server and CDN settings that break association

## apple-app-site-association

Served at `https://example.com/.well-known/apple-app-site-association`, no file extension,
`Content-Type: application/json`, no redirect. Apple documents a size limit for the file
(128 KB uncompressed at the time of writing); a file generated from a large route list can
cross it, so check the size.

```json
{
  "applinks": {
    "details": [
      {
        "appIDs": ["ABCDE12345.com.example.app"],
        "components": [
          { "/": "/account/delete*", "exclude": true, "comment": "web-only flow" },
          { "/": "/orders/*" },
          { "/": "/invite/*", "?": { "code": "?*" } },
          { "/": "/p/*" }
        ]
      }
    ]
  }
}
```

- `appIDs` is team ID, a dot, and bundle ID. List every app that should claim these paths
  (for example the production app and an internal build with a different bundle ID).
- `components` are tried in order and the first match decides, so an exclusion must come
  before the broader include it carves out of.
- `?` matches query items and `#` the fragment; `*` matches any run of characters and `?`
  inside a value matches one character.
- Older files use `appID` and `paths`; current iOS reads `components`. Keep the old keys
  only if you still support an iOS version that needs them.
- The entitlement side: Associated Domains lists `applinks:example.com` and
  `applinks:www.example.com` separately. `applinks:*.example.com` covers subdomains but
  not the apex.

## assetlinks.json

Served at `https://example.com/.well-known/assetlinks.json`, `Content-Type:
application/json`, no redirect.

```json
[
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "android_app",
      "package_name": "com.example.app",
      "sha256_cert_fingerprints": [
        "AA:BB:...:FF"
      ]
    }
  }
]
```

- The fingerprint list holds every signing certificate whose builds must verify: the Play
  app signing key (from Play Console) for store installs, and the upload or debug keys
  only if those builds need verified links.
- Google's Digital Asset Links API shows what the verifier reads:
  `https://digitalassetlinks.googleapis.com/v1/statements:list?source.web.site=https://example.com&relation=delegate_permission/common.handle_all_urls`.

## The Android intent filter

```xml
<activity android:name=".MainActivity" android:exported="true"
          android:launchMode="singleTop">
  <intent-filter android:autoVerify="true">
    <action android:name="android.intent.action.VIEW" />
    <category android:name="android.intent.category.DEFAULT" />
    <category android:name="android.intent.category.BROWSABLE" />
    <data android:scheme="https" />
    <data android:host="example.com" />
    <data android:host="www.example.com" />
    <data android:pathPrefix="/orders" />
    <data android:pathPrefix="/invite" />
  </intent-filter>
</activity>
```

- `data` elements in one filter combine: every scheme with every host with every path.
  Put routes that need different handling in separate filters.
- Keep custom-scheme filters (`myapp://`) in a separate filter without `autoVerify`; they
  cannot be verified and should not carry anything sensitive.
- With `singleTop` or `singleTask`, a link while the activity is open arrives in
  `onNewIntent`, not `onCreate`.

## Server and CDN settings that break association

| Setting | Effect | Fix |
| --- | --- | --- |
| HTTP-to-HTTPS or apex-to-www redirect on the well-known path | Verification fails | Serve the file directly on every host |
| Trailing-slash or locale redirect | Same | Exempt `/.well-known/` from the rule |
| Bot challenge, WAF rule or geo-block | The fetcher gets a challenge page | Allow the well-known paths through |
| Login wall or basic auth on a staging host | Same | Allow the well-known paths, or use developer mode for staging |
| Wrong content type (`text/plain`, `application/octet-stream`) | Rejected or ignored | Set `application/json` explicitly for the extensionless AASA |
| Long cache lifetime on the file | Old content served after a fix | Short cache lifetime on both files |
| Single-page app fallback serving `index.html` for unknown paths | `200 text/html` instead of the file | Route the well-known paths before the fallback |
