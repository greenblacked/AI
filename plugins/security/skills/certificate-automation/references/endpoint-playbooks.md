# Endpoint playbooks

Read this once an endpoint has been classified under the skill's step 2. Each section
below is the automation path for one class, plus the runbook shape for the class that
cannot automate at all.

## Contents

- [Native ACME client](#native-acme-client)
- [Orchestrator-managed (cert-manager)](#orchestrator-managed-cert-manager)
- [Cloud-managed](#cloud-managed)
- [Appliance with no ACME support](#appliance-with-no-acme-support)
- [Multi-cloud inventory commands](#multi-cloud-inventory-commands)

## Native ACME client

`certbot` is the reference client. Choose the plugin that matches how the endpoint
actually serves TLS, not a generic HTTP-01 challenge if the host cannot expose port 80
to the internet.

```bash
# HTTP-01, for a host that can serve a challenge file on port 80
certbot certonly --standalone -d host.example.com --deploy-hook "systemctl reload nginx"

# DNS-01, for a host behind a firewall or for a wildcard certificate
certbot certonly --dns-route53 -d '*.example.com' -d example.com

# Verify the renewal path works before relying on the timer
certbot renew --dry-run

# The renewal timer's unit name depends on how certbot was installed — find it before enabling it
systemctl list-timers --all | grep -i certbot
```

Enable whichever unit that command shows rather than assuming a name: `certbot-renew.timer` on an EPEL install, `certbot.timer` from Debian or Ubuntu's `apt` package, or `snap.certbot.renew.timer` from the snap. `systemctl` changes host state, so it is deliberately outside this skill's `allowed-tools` and should prompt rather than run unattended.

Two things to confirm once the client is running, not only once:

- `certbot renew` checks ACME Renewal Information automatically from 4.1.0 onward. Confirm
  the installed version with `certbot --version` before assuming ARI is in effect; an
  older pinned version silently falls back to the lifetime-fraction rule only.
- The `deploy-hook` (or `renew-hook`) actually reloads the consuming service. A renewed
  certificate that is never reloaded into the running process is functionally still the
  old certificate until the next restart.

## Orchestrator-managed (cert-manager)

`cert-manager` issues and renews `Certificate` resources against an `Issuer` or
`ClusterIssuer` that points at an ACME CA.

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: acme-issuer
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: certs@example.com
    privateKeySecretRef:
      name: acme-issuer-key
    solvers:
      - http01:
          ingress:
            ingressClassName: nginx
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: host-example-com
spec:
  secretName: host-example-com-tls
  dnsNames:
    - host.example.com
  issuerRef:
    name: acme-issuer
    kind: ClusterIssuer
```

Per `cert-manager`'s `Certificate` type, leaving both `renewBefore` and `renewBeforePercentage`
unset already renews at a third of the certificate's issued lifetime — the same fraction
as this skill's lifetime-fraction backstop, and one that scales automatically as the
estate's certificates move from 398 days down to 47 under the Baseline Requirements
schedule. Leave `renewBeforePercentage` unset for that default; set it, for example to
`50`, only when one certificate genuinely needs to renew earlier than the estate default.

```bash
# Estate-wide renewal status, across every namespace
kubectl get certificate -A \
  -o custom-columns=NAME:.metadata.name,READY:.status.conditions[0].status,NOTAFTER:.status.notAfter

# The last issuance or renewal attempt's detail, for anything not Ready
kubectl describe certificaterequest -n NAMESPACE
```

## Cloud-managed

A cloud-managed certificate service renews on its own as long as the domain-validation
method it depends on stays in place. The recurring failure here is not the renewal
itself; it is the validation record disappearing when a workload, a DNS zone, or a
delegated subdomain moves.

```bash
# AWS Certificate Manager: status and the validation records it expects to find
aws acm describe-certificate --certificate-arn ARN_EXAMPLE \
  --query 'Certificate.{status:Status,validation:DomainValidationOptions}'

# GCP-managed certificates on a load balancer
gcloud compute ssl-certificates describe CERT_NAME --format='value(managed.status,managed.domainStatus)'

# Azure App Service managed certificate
az webapp config ssl list --resource-group RG_EXAMPLE
```

Confirm the validation record on every review, not only at setup: a `Status` other than
issued or active almost always means the validation record was removed, and the fix is
restoring the record rather than reissuing the certificate.

## Appliance with no ACME support

Some endpoints cannot run an ACME client and cannot be handed to an orchestrator:
firewalls, some load balancers, vendor SaaS admin consoles, embedded device firmware. The
goal for this class is not automation — it does not exist yet — it is making the manual
process survive the lifetime cuts on 2026-03-15, 2027-03-15 and 2029-03-15 rather than
quietly falling behind them.

A runbook for this class needs, at minimum:

- **A named owner**, not a team name. The renewal has to land on one person's calendar.
- **A reminder set from the lifetime-fraction rule against the appliance's actual
  certificate validity**, not a fixed number of days that was correct once and never
  revisited.
- **The exact console path or command**, screenshotted or scripted, because the person
  who did it last time may not be the person doing it this time.
- **A rollback step**: the previous certificate's location and how to reinstall it if the
  new one is rejected by the appliance.
- **An escalation contact** for the vendor, for the case where the appliance's own
  interface cannot complete a renewal and support has to be engaged — file this before
  the certificate is close to expiry, not after.

Track every appliance in this class explicitly in the estate inventory from step 1, with
its next renewal date, so the schedule shrinking under the Baseline Requirements does not
silently outrun a manual process nobody revisited.

## Multi-cloud inventory commands

Use these when reconciling the inventory in step 1 against what each cloud account
actually holds, rather than only what a certificate management tool reports.

```bash
aws acm list-certificates --query 'CertificateSummaryList[].{arn:CertificateArn,domain:DomainName,expiry:NotAfter}'
gcloud compute ssl-certificates list --format='table(name,type,expireTime)'

# az webapp config ssl list is scoped to one resource group; repeat it per group, or list
# every App Service certificate across the whole subscription instead
az webapp config ssl list --resource-group RG_EXAMPLE --query '[].{name:name,expirationDate:expirationDate}'
az resource list --resource-type Microsoft.Web/certificates --query '[].{name:name,resourceGroup:resourceGroup}'
```

A certificate present in one of these listings but absent from the tracked inventory is
exactly the finding step 1 is looking for — resolve it the same way, with an owner and a
classification, before moving on.
