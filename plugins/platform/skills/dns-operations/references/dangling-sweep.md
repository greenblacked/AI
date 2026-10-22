# Dangling record sweep

Read this before running the sweep in step 4. It covers exporting records, a sweep script
that flags candidates, the ownership checks that turn a candidate into a finding, and what
to do with a finding. This is defensive procedure for zones you operate.

## Contents

- Exporting records
- The sweep script
- Ownership checks
- Triage and removal

## Exporting records

The sweep reads a tab-separated file with three columns: name, type, value.

Route 53, including alias records, which are the easiest to miss:

```bash
aws route53 list-resource-record-sets --hosted-zone-id Z0123456789ABC \
  | jq -r '.ResourceRecordSets[] | .Name as $n
      | if .AliasTarget then [$n, "ALIAS", .AliasTarget.DNSName]
        else .Type as $t | (.ResourceRecords // [])[] | [$n, $t, .Value] end
      | @tsv' > records.tsv
```

Cloud DNS:

```bash
gcloud dns record-sets list --zone=example-zone --format=json \
  | jq -r '.[] | .name as $n | .type as $t | .rrdatas[] | [$n, $t, .] | @tsv' > records.tsv
```

Azure DNS: `az network dns zone export` writes the zone as a BIND-format file; convert
its CNAME, NS, MX, A and AAAA lines to the same three columns.

For a zone kept in code, the code is the inventory, but export from the provider anyway:
the difference between the two is drift, and drift is where forgotten records live.

## The sweep script

Save it outside the directory holding the export, make it executable, and run it as
`./sweep.sh records.tsv example.com.` with the zone apex as the second argument. It
prints one line per candidate and changes nothing.

```bash
#!/usr/bin/env bash
# Flag DNS records whose targets may no longer belong to you. Read-only.
set -Eeuo pipefail

records=$1
apex=$2

status_of() {
  local s
  s=$(dig +noall +comments +time=3 +tries=2 "$1" "$2" </dev/null 2>/dev/null \
      | grep -o 'status: [A-Z]*' | head -n 1 | cut -d' ' -f2) || true
  echo "${s:-NO-ANSWER}"
}

provider_hosted='s3-website|\.s3[.-]([a-z0-9-]+\.)?amazonaws\.com|cloudfront\.net|elasticbeanstalk\.com|azurewebsites\.net|cloudapp\.azure\.com|trafficmanager\.net|blob\.core\.windows\.net|herokuapp\.com|github\.io|storage\.googleapis\.com'

while IFS=$'\t' read -r name type value; do
  case "$type" in
    CNAME|ALIAS)
      s=$(status_of "$value" A)
      if [[ $s != NOERROR ]]; then
        printf 'DANGLING\t%s\t%s\t%s\t%s\n' "$name" "$type" "$value" "$s"
      elif grep -Eq "$provider_hosted" <<<"$value"; then
        printf 'VERIFY-OWNER\t%s\t%s\t%s\n' "$name" "$type" "$value"
      fi
      ;;
    NS)
      [[ $name == "$apex" ]] && continue
      header=$(dig +norecurse +noall +comments +time=3 +tries=2 "@$value" "$name" SOA \
               </dev/null 2>/dev/null) || true
      if ! grep -q 'status: NOERROR' <<<"$header" || ! grep -Eq 'flags:[a-z ]* aa' <<<"$header"; then
        printf 'LAME-DELEGATION\t%s\t%s\n' "$name" "$value"
      fi
      ;;
    MX)
      target=${value##* }
      s=$(status_of "$target" A)
      [[ $s == NOERROR ]] || printf 'DANGLING\t%s\tMX\t%s\t%s\n' "$name" "$target" "$s"
      ;;
    A|AAAA)
      if ! grep -Eq '^(10\.|172\.(1[6-9]|2[0-9]|3[01])\.|192\.168\.|127\.|f[cd])' <<<"$value"; then
        printf 'VERIFY-IP\t%s\t%s\t%s\n' "$name" "$type" "$value"
      fi
      ;;
  esac
done <"$records"
```

`DANGLING` and `LAME-DELEGATION` lines are findings unless the target is down for a known,
temporary reason. `VERIFY-OWNER` and `VERIFY-IP` lines are candidates for the checks below.
The provider pattern list is a starting set, not a complete one; add the hosting and SaaS
providers your organisation uses.

## Ownership checks

| Target | Check | Dangling when |
| --- | --- | --- |
| S3 bucket or website endpoint (for a website alias, the bucket name is the record name) | `aws s3api head-bucket --bucket NAME` from your account | 404: nobody owns the bucket and anyone can create it. 403: someone else already does, which is worse |
| CloudFront distribution | `aws cloudfront list-distributions --query "DistributionList.Items[].Aliases.Items[]"` | Your name is not an alias on any distribution you own |
| Elastic Beanstalk | `aws elasticbeanstalk describe-environments --query "Environments[].CNAME"` | The target is not in the list |
| Azure App Service | `az webapp list --query "[].defaultHostName"` | The target is not in the list |
| Other SaaS or hosting | The custom-domain setting in that provider's account | The name is not configured in an account you control |
| Cloud public IP | `aws ec2 describe-network-interfaces --filters Name=association.public-ip,Values=IP` and `aws ec2 describe-addresses --public-ips IP` in each region, or the provider's equivalent | Neither lists the address. An Elastic IP you own but have not attached appears only in the second; it is not dangling, though it is waste |
| NS delegation | Query each delegated server for the subzone's SOA, as the script does | Not authoritative, refused, or no answer |

An A record pointing at a load balancer's current addresses is a defect even when it works
today: those addresses change. Replace it with an alias or a CNAME to the load balancer's
name.

## Triage and removal

1. **Remove the record** through the zone's normal code path, expedited. The record is the
   vulnerability; nothing else needs to be understood first.
2. **Check whether it was claimed.** Request the name and see what answers. Search
   certificate-transparency logs for certificates issued for the name that you did not
   request. Either is a security incident, not a cleanup: content served under your domain
   can phish users and, depending on cookie scope, read cookies set for the parent domain.
3. **Find why it dangled.** Usually a decommission that deleted the resource but not the
   record. Add "remove DNS records" to the decommission checklist that missed it.
4. **Record the finding** with the date found, date removed and whether it was claimed.
