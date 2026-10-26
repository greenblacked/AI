# Summary-first checklist

Use during an efficiency pass on an active REA investigation.

1. Confirm the question still needs REA (shipped artifact / decompilation /
   runtime evidence), not ordinary source tools.
2. List calls already made and their Evidence IDs; reuse before reopen.
3. For the next expensive call, request summary/default detail first.
4. Page with `inspect_analysis_view` / retained parent IDs for the missing
   section only.
5. If MCP reports a transport `resource_constraint`, shrink the view or export;
   do not repeat the producer unchanged.
6. For JavaScript graphs, resolve module `node_id` before broad traces.
7. Close native sessions (`close_binary`) when the investigation is complete so
   providers release resources.
8. Record what stayed unproven so a later pass does not re-litigate settled
   unknowns.
