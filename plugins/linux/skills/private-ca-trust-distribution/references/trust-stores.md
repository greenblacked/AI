# Trust stores by runtime

One row per place a CA can be trusted. Always add the internal root; never remove the
public ones.

| Runtime | Where trust lives | How to add the root | How to verify |
| --- | --- | --- | --- |
| Debian and Ubuntu OS | `/etc/ssl/certs/ca-certificates.crt` | PEM with `.crt` extension in `/usr/local/share/ca-certificates/`, then `update-ca-certificates` | `openssl verify -CAfile /etc/ssl/certs/ca-certificates.crt leaf.pem` |
| RHEL family OS | `/etc/pki/tls/certs/ca-bundle.crt` | PEM in `/etc/pki/ca-trust/source/anchors/`, then `update-ca-trust` | `trust list` and `openssl verify` |
| curl | OS bundle by default; `--cacert FILE`, or `CURL_CA_BUNDLE` | Use the OS bundle; a file-only override replaces the defaults | `curl -sS https://host/` without `-k` |
| Python requests | `certifi` bundle, unless `REQUESTS_CA_BUNDLE` (or `CURL_CA_BUNDLE`) is set; `SSL_CERT_FILE` does not affect requests, only stdlib `ssl`/`urllib` defaults | Set `REQUESTS_CA_BUNDLE` to the OS bundle that includes the root | `python3 -c "import requests;print(requests.get('https://host').status_code)"` |
| pip | `pip config` key `global.cert`, or `PIP_CERT` | Point at the OS bundle | `pip download` against the internal index |
| Node.js | built-in list plus `NODE_EXTRA_CA_CERTS` | Set `NODE_EXTRA_CA_CERTS` to a PEM file holding the root; it extends the built-in list | `node -e "require('https').get('https://host',r=>console.log(r.statusCode))"` |
| npm | `cafile` setting, or the Node variable above | Prefer `NODE_EXTRA_CA_CERTS`; `npm config set cafile` replaces npm's default list | `npm ping` |
| Go | system store; `SSL_CERT_FILE` and `SSL_CERT_DIR` override on Linux | OS bundle, or the variable | a small client or `go get` |
| Java | `$JAVA_HOME/lib/security/cacerts` | `keytool -importcert -trustcacerts -alias internal-root -file ca.pem -keystore CACERTS_PATH`; the default store password is documented by the vendor and should be changed in managed images. On Debian, the `ca-certificates-java` hook copies OS roots into it. | `keytool -list -keystore CACERTS_PATH -alias internal-root` |
| git | OS bundle; `http.sslCAInfo` setting | `git config --system http.sslCAInfo FILE` only when the OS bundle is not used | `git ls-remote https://host/repo.git` |
| Docker daemon and registries | `/etc/docker/certs.d/HOST:PORT/ca.crt` per registry | Place the root there; no daemon restart is needed for that directory | `docker pull HOST:PORT/image` |
| Firefox | its own store | Enterprise policy `Certificates`, including importing the OS enterprise roots | open an internal HTTPS page |
| Chrome and Chromium on Linux | NSS database under the user's `.pki/nssdb` | `certutil` against that database, or a managed policy | open an internal HTTPS page |

## Checks that catch the common mistakes

- Compare the fingerprint of the installed file with the published value:
  `openssl x509 -in installed.pem -noout -fingerprint -sha256`.
- A bundle file holds many PEM blocks. Count them: `grep -c 'BEGIN CERTIFICATE' bundle.pem`.
  A count of 1 after you "extended" the bundle means you replaced it.
- A chain served without its intermediate fails in curl and Java but may pass in a browser;
  that is a server fault and belongs to `tls-handshake-debugging`.
- Containers inherit nothing from the host. The root has to be in the image or mounted.

## Rotation timeline

1. Publish the new root and its fingerprint.
2. Distribute it to every store listed above; verify by sampling each runtime.
3. Only then let the CA issue leaves under the new root.
4. Keep the old root installed until the last certificate it signed has expired.
5. Remove the old root from images at the next rebuild, and record the date.
