# Finding overlap and checking redirects

Read this at steps 3 and 4, when grouping pages by query and writing the table.

## Contents

- Overlap grouping
- Choosing the surviving URL
- Redirect table checks

## Overlap grouping

Export query and page pairs from Search Console for twelve months. Keep queries where two or more of your pages received impressions. Rank by total clicks for the query. For each group list the pages, their clicks and impressions per query, positions, and links. Pages that alternate in the results for the same query, or that split clicks, are the cannibalisation candidates; read them to confirm they answer the same question.

## Choosing the surviving URL

Prefer, in order: the page with the most referring domains, then the most clicks, then the better URL (shorter, permanent, no date in it), then the more recent. Move the useful sections of the others into it before redirecting, and update the headline if the merged page now covers more.

## Redirect table checks

- Every source appears once.
- No target is itself a source (chains) and no target redirects to a source (loops).
- Every target returns 200, is indexable and is canonical to itself.
- The target is topically close; if none is, the source is a 410 candidate, not a redirect to a general page.
- Pages with referring domains are redirected, not removed.
- The sitemap lists targets only, and no internal link points at a source.
- Gone pages return 410 rather than a 200 page saying "not found".
