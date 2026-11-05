"""Behaviour tests for the twenty-nine kit hooks under `plugins/*/skills/*/assets/hooks/`.

`tests/test_plugin_shape.py` checks what a hook is allowed to look like; this file runs
each one. The cases live in `tests/fixtures/kit_hooks.json` as data: a hook, a payload,
the exit code it must give and a name. Every bypass a review has found and every false
positive a fix has had to avoid is a row there, so a later change to a pattern cannot
quietly reopen one.

Each case runs twice, once with `jq` as the only parser on PATH and once with `python3`
only, because the hooks carry both and they must agree. The environment is minimal
(`env`-style, `LANG=C.UTF-8`), and the working directory holds a `json.py` that would make
a hook allow everything if a bare `python3 -c` imported it; a case that expects a block
therefore also proves the stub did not run.

A large payload per hook must stay within a CPU budget, set below. A hook that outlasts the hook
timeout fails open, so a hang here is a finding, and the subprocess timeout makes it fail
only its own case.
"""

import json
import resource
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TABLE = json.loads((Path(__file__).parent / "fixtures" / "kit_hooks.json").read_text("utf-8"))

HOOK_FILES = {
    "tf": "refuse-unsaved-terraform-apply",
    "kill": "block-set-based-backend-kill",
    "sup": "require-suppression-reason",
    "sym": "keep-shipped-symbols",
    "erase": "block-whole-device-erase",
    "ddl": "block-destructive-warehouse-ddl",
    "retry": "retry-without-deadline",
    "gen": "generated-stamp-guard",
    "mail": "email-template-unsubscribe",
    "ph": "placeholder-list",
    "game": "game-data-json",
    "because": "decision-rule-because",
    "unit": "exec-absolute-path",
    "safety": "require-safety-comment",
    "closed": "require-closed-object-schema",
    "otelmem": "collector-memory-limiter",
    "conn": "connection-ceilings",
    "churn": "require-churn-evidence",
    "mem": "require-memory-request",
    "lock": "close-lock-date",
    "dmap": "drift-map-ignore-reason",
    "sleep": "no-fixed-sleep-in-tests",
    "wfrun": "flag-untrusted-field-in-run",
    "css": "flag-viewport-width-css",
    "slice": "slice-waiver-placement",
    "adr": "require-considered-options",
    "rbk": "runbook-stamp",
    "wkrev": "weekly-review-shape",
    "tlsoff": "tls-verification-off",
}

# Everything a hook may call besides its parser. A tool a hook starts using that is not here
# fails the whole table, which is the point: the hook has gained a dependency.
BASE_TOOLS = ("bash", "cat", "grep", "sed", "tr", "wc", "head", "awk")

# A tool only one hook may call, kept out of BASE_TOOLS so that another hook starting to use it
# still fails. `tail` is for game-data-json in its jq mode, which skips a byte order mark with
# `tail -c +4`.
EXTRA_TOOLS = {"game": ("tail",)}

MODES = {"jq": ("jq",), "python3": ("python3",)}

# A json.py that a bare `python3 -c` would import from the working directory. It reports no
# tool input, so a hook that ran it would allow everything; it also leaves a marker file.
STUB_JSON = (
    "import pathlib\n"
    "pathlib.Path('STUB_JSON_RAN').write_text('ran')\n"
    "def load(f):\n"
    "    return {}\n"
    "def dumps(v):\n"
    "    return ''\n"
)

# The real verification-record template, so the rbk rows judge the file the kit ships.
RBK_RECORD = (
    ROOT / "plugins/operations/skills/runbook/assets/templates/runbook-verification-record.md"
).read_text("utf-8")

WF_STEPS = "jobs:\n  a:\n    steps:\n"

CHURN_HEADER = "Account,Dropdown,Primary code,Key evidence\n"

SCRATCH_FILES = {
    "json.py": STUB_JSON,
    "tfplan": "plan",
    "apply.log": "log",
    "x/tfplan": "plan",
    "applications/bad.md": "Dear team\n[TK: company]\n",
    "applications/-n.md": "[TK: company]\n",
    "applications/good.md": "[TK: company]\n## Placeholders to fill\n- company\n",
    "applications/ok.md": "Dear team\n",
    "applications/dir.md/.keep": "",
    "cv/bad.md": "[TK: role]\n",
    # game-data-json reads the written file; a file outside data/ is invalid on purpose so that
    # an allow proves the hook never opened it.
    "data/valid.json": '{"a": [1, 2]}',
    "data/invalid.json": '{"a": ',
    "data/two.json": "1 2",
    "data/empty.json": "",
    "data/bom.json": '\ufeff{"a": 1}',
    "data/bom-bad.json": '\ufeff{"a": ',
    "data/invalid.txt": "{",
    "other/invalid.json": "{",
    "-x/data/invalid.json": "{",
    "-x/data/valid.json": "{}",
    # because: decision-rule-because
    "interviews/decision-rule-bad.md": "- If the batch ran late, check the lock\n\nplain\n",
    "interviews/billing/deep/decision-rule-bad.md": "- If the batch ran late, check it\n\nplain\n",
    "interviews/-decision-rule.md": "If x, y\n",
    "interviews/decision-rule-second-bad.md": "- If a, b because c\n- If d, e\n",
    "interviews/decision-rule-wrapped-bad.md": "If a, b\ncontinues\n\nbecause later\n",
    "interviews/decision-rule-wrapped-good.md": (
        "- If the batch ran late, check the lock first\n  because stalls start there\n"
    ),
    "interviews/decision-rule-good.md": "- If a, b because c\n",
    "interviews/decision-rule-capital.md": "If a, b. Because c\n",
    "interviews/decision-rule-no-rule.md": "Walk me through it\n",
    "interviews/decision-rule-lower-if.md": "if x then y\n",
    "interviews/decision-rule-iffy.md": "Iffy result\nIf\n",
    "interviews/transcript.md": "If the batch ran late I looked at the lock\n",
    "interviews/decision-rule-sheet.md": "- If the batch ran late, check the lock\n",
    "interviews/note.txt": "If x, y\n",
    "interviews/decision-rule-dir.md/.keep": "",
    "notes/decision-rules-a.md": "If x, y\n",
    "notes/other.md": "If x, y\n",
    # unit: exec-absolute-path
    "units/good.service": (
        "[Unit]\nDescription=x\n[Service]\nExecStart=/usr/bin/app --flag\n"
        "ExecStartPre=-/usr/bin/true\nRestart=on-failure\nRestartSec=5\n"
    ),
    "units/relative.service": "[Service]\nExecStart=./server\n",
    "units/relative-dir.service": "[Service]\nExecStart=bin/run --x\n",
    "units/bare.service": "[Service]\nExecStart=server --x\n",
    "units/specifier.service": "[Service]\nExecStart=%h/bin/app\n",
    "units/app.service.d/override.conf": ("[Service]\nExecStart=\nExecStart=/opt/app/bin/app\n"),
    "units/bad.service.d/override.conf": "[Service]\nExecStart=\nExecStart=-@./app\n",
    "units/prefix-bad.service": "[Service]\nExecStartPre=!!./prep\n",
    "units/continued.service": "[Service]\nExecStart=\\\n  ../bin/app \\\n  --x\n",
    "units/continued-ok.service": ("[Service]\nExecStart=\\\n  /usr/bin/app \\\n  ./arg\n"),
    "units/comment.service": (
        "[Service]\n# ExecStart=./old\n; ExecStart=bin/old\nExecStart=/usr/bin/app\n"
    ),
    "units/crlf.service": "[Service]\r\nExecStart=./x\r\n",
    "units/no-exec.service": "[Unit]\nDescription=x\n",
    "units/stop-bad.service": "[Service]\nExecStart=/usr/bin/app\nExecStop=./stop\n",
    "units/quoted-bad.service": '[Service]\nExecStart="./app" x\n',
    "units/mid-line.service": (
        "[Service]\nEnvironment=ExecStart=./x\nDescription=ExecStart=bin/x\n"
    ),
    "units/relative.txt": "[Service]\nExecStart=./server\n",
    "units/empty.service": "",
    "units/dir.service/.keep": "",
    "-x/units/bad.service": "[Service]\nExecStart=./server\n",
    "-x/units/good.service": "[Service]\nExecStart=/usr/bin/app\n",
    # safety: require-safety-comment
    "rust/block-ok.rs": (
        "fn f() {\n    // SAFETY: p is non-null, checked above.\n    let a = unsafe { *p };\n}\n"
    ),
    "rust/block-bare.rs": "fn f() {\n    let a = unsafe { *p };\n}\n",
    "rust/block-second-bare.rs": (
        "fn f() {\n    // SAFETY: p is non-null.\n    let a = unsafe { *p };\n"
        "    let b = unsafe { *q };\n}\n"
    ),
    "rust/fn-bare.rs": "pub unsafe fn f() {}\n",
    "rust/fn-doc.rs": (
        "/// Reads the cell.\n///\n/// # Safety\n/// The caller must hold the lock.\n"
        "#[inline]\npub unsafe fn f() {}\n"
    ),
    "rust/fn-comment.rs": "// SAFETY: only called from init.\nunsafe fn f() {}\n",
    "rust/impl-bare.rs": "unsafe impl Send for X {}\n",
    "rust/impl-ok.rs": (
        "// SAFETY: X owns its pointer and never aliases it.\n"
        "// Sync follows because all access is under the mutex.\n"
        "unsafe impl Sync for X {}\n"
    ),
    "rust/impl-doc-only.rs": (
        "/// # Safety\n/// Documented like a function.\nunsafe impl Send for X {}\n"
    ),
    "rust/trait-bare.rs": "pub unsafe trait Zeroable {}\n",
    "rust/trait-doc.rs": (
        "/// # Safety\n/// Implementers must be valid when all-zero.\n"
        "pub unsafe trait Zeroable {}\n"
    ),
    "rust/blank-between.rs": "// SAFETY: ok\n\nlet a = unsafe { 1 };\n",
    "rust/code-between.rs": "// SAFETY: ok\nlet x = 1;\nlet a = unsafe { 1 };\n",
    "rust/same-line.rs": "let a = unsafe { 1 }; // SAFETY: constant is in range\n",
    "rust/crlf.rs": "// SAFETY: ok\r\nlet a = unsafe { 1 };\r\n",
    "rust/extern-block-bare.rs": ('unsafe extern "C" {\n    fn abs(x: i32) -> i32;\n}\n'),
    "rust/extern-fn-bare.rs": 'pub unsafe extern "C" fn cb() {}\n',
    "rust/no-sites.rs": (
        "#![forbid(unsafe_code)]\n#[allow(unsafe_op_in_unsafe_fn)]\n"
        "#[unsafe(no_mangle)]\ntype F = unsafe fn(i32);\nlet unsafe_code = 1;\n"
        'let s = "unsafe { not code }";\n// unsafe { in a comment }\n'
        "/// unsafe fn in docs\n"
    ),
    "rust/no-unsafe.rs": "fn main() {}\n",
    "rust/not-rust.txt": "unsafe { x }\n",
    "-x/unsafe.rs": "unsafe { x }\n",
    "rust/dir.rs/.keep": "",
    # closed: require-closed-object-schema
    "schemas/closed.json": (
        '{"type":"object","properties":{"category":{"type":"string","enum":["a","other"]},"tags":{"type":"array","items":{"type":"object","properties":{"k":{"type":"string"}},"required":["k"],"additionalProperties":false}}},"required":["category","tags"],"additionalProperties":false}'
    ),
    "schemas/open.json": (
        '{"type":"object","properties":{"a":{"type":"string"}},"required":["a"]}'
    ),
    "schemas/nested-open.json": (
        '{"type":"object","properties":{"items":{"type":"array","items":{"type":"object","properties":{"k":{"type":"string"}}}}},"additionalProperties":false}'
    ),
    "schemas/anyof-open.json": (
        '{"type":"object","properties":{"a":{"anyOf":[{"type":"object","properties":{}},{"type":"null"}]}},"additionalProperties":false}'
    ),
    "schemas/nullable-open.json": '{"type":["object","null"],"properties":{}}',
    "schemas/map-open.json": ('{"type":"object","additionalProperties":{"type":"string"}}'),
    "schemas/envelope-open.json": (
        '{"name":"t","strict":true,"schema":{"type":"object","properties":{"a":{"type":"string"}},"additionalProperties":true}}'
    ),
    "schemas/tricky-closed.json": (
        '{"type":"object","properties":{"type":{"type":"string","enum":["object"]},"properties":{"type":"string"}},"additionalProperties":false,"examples":[{"type":"object","properties":{}}],"default":{"type":"object"}}'
    ),
    "schemas/array.json": "[1, 2]",
    "schemas/invalid.json": '{"type":"object","properties":{"a":',
    "schemas/two.json": "{} {}",
    "schemas/empty.json": "",
    "schemas/open.txt": "{",
    "schemas/dir.json/.keep": "",
    "other/open-schema.json": '{"type":"object","properties":{}}',
    "nested/schemas/deep/open.json": '{"type":"object","properties":{}}',
    "schemas/many-open.json": json.dumps(
        {
            "type": "object",
            "properties": {f"p{i}": {"type": "object", "properties": {}} for i in range(4000)},
            "additionalProperties": False,
        }
    ),
    # otelmem: collector-memory-limiter
    "otel-collector-good.yaml": (
        "service:\n  pipelines:\n    traces:\n      receivers: [otlp]\n"
        "      processors: [memory_limiter, batch]\n      exporters: [debug]\n"
        "    metrics:\n      receivers: [otlp]\n      processors:\n"
        "        - memory_limiter/main\n        - batch\n      exporters: [debug]\n"
    ),
    "otelcol/bad.yml": (
        "processors:\n  memory_limiter:\n    limit_percentage: 80\n  batch:\nservice:\n"
        "  pipelines:\n    traces:\n      receivers: [otlp]\n      processors:\n"
        "        - batch\n      exporters: [debug]\n"
    ),
    "otel-collector-flow-bad.yaml": (
        "service:\n  pipelines:\n    logs:\n      receivers: [otlp]\n"
        "      processors: [batch, resource]\n      exporters: [debug]\n"
    ),
    "otel-collector-second-bad.yaml": (
        "service:\n  pipelines:\n    traces:\n"
        "      processors: [memory_limiter, batch]\n    metrics:\n"
        "      processors: [batch]\n"
    ),
    "otel-collector-comment-bad.yaml": (
        "service:\n  pipelines:\n    traces:\n      processors: [batch] # memory_limiter later\n"
    ),
    "otel-collector-crlf.yaml": ("pipelines:\r\n  t:\r\n    processors:\r\n      - batch\r\n"),
    "otel-collector-multiline.yaml": (
        "service:\n  pipelines:\n    traces:\n      processors: [batch,\n        memory_limiter]\n"
    ),
    "otel-collector-empty.yaml": (
        "service:\n  pipelines:\n    traces:\n      receivers: [otlp]\n"
        "      processors: []\n    metrics:\n      receivers: [otlp]\n"
    ),
    "otel-collector-nopipes.yaml": "receivers:\n  otlp:\nprocessors:\n  batch:\n",
    "config/otel-bad.yaml": ("service:\n  pipelines:\n    traces:\n      processors: [batch]\n"),
    # conn: connection-ceilings
    "sysctl.conf": "net.ipv4.tcp_tw_recycle = 1\n",
    "sysctl.d/conn-nocomment.conf": "net.netfilter.nf_conntrack_max = 262144\n",
    "sysctl.d/conn-port-nocomment.conf": ("net.ipv4.ip_local_port_range = 1024 65000\n"),
    "sysctl.d/conn-recycle.conf": ("# kept for old clients, 2016\nnet.ipv4.tcp_tw_recycle = 1\n"),
    "sysctl.d/conn-recycle-slash.conf": "-net/ipv4/tcp_tw_recycle=1\n",
    "sysctl.d/conn-blank.conf": (
        "# nf_conntrack_count peaked at 61000 of 65536\n\nnet.netfilter.nf_conntrack_max = 262144\n"
    ),
    "sysctl.d/conn-words.conf": (
        "# raise it for the new cluster\nnet.netfilter.nf_conntrack_max = 262144\n"
    ),
    "sysctl.d/conn-ok.conf": (
        "# nf_conntrack_count peaked at 61000 of 65536 on 2026-05-01\n"
        "net.netfilter.nf_conntrack_max = 262144\n"
    ),
    "sysctl.d/conn-other.conf": "vm.swappiness = 10\nnet.core.somaxconn = 4096\n",
    "sysctl.d/conn-commented.conf": (
        "# net.ipv4.tcp_tw_recycle = 1\n; net.ipv4.tcp_tw_recycle = 1\n"
    ),
    "sysctl.d/conn-nocomment.txt": "net.netfilter.nf_conntrack_max = 262144\n",
    "other/conn-nocomment.conf": "net.netfilter.nf_conntrack_max = 262144\n",
    "sysctl.dist/conn-nocomment.conf": "net.netfilter.nf_conntrack_max = 262144\n",
    "-x/sysctl.d/conn-nocomment.conf": "net.netfilter.nf_conntrack_max = 262144\n",
    # churn: require-churn-evidence
    "churn/blank.csv": (
        "Account,Dropdown,Primary code,Key evidence\n1,Price,Missing capability,\n"
    ),
    "churn/na.csv": (
        "Account,Dropdown,Primary code,Key evidence\n1,Price,Missing capability, N/A \n"
    ),
    "churn/short.csv": ("Account,Dropdown,Primary code,Key evidence\n1,Price,Missing capability\n"),
    "churn/titled.csv": (
        "Q3 sample\nAccount,Dropdown,Primary code,Key evidence\n1,Price,Missing capability,\n"
    ),
    "churn/bom.csv": "\ufeffAccount,PRIMARY CODE,key evidence\n1,Usage declined,\n",
    "churn/open.csv": (
        'Account,Dropdown,Primary code,Key evidence\n1,Price,Usage declined,"open\n'
        "2,Price,Champion left,x\n"
    ),
    "churn/swapped.csv": "Key evidence,Primary code\n,Champion left\n",
    "churn/uncoded-blank.csv": (
        "Account,Primary code,Key evidence,Confidence\n"
        "7,,uncoded: no usable evidence in notes or tickets,uncoded\n"
    ),
    "churn/uncoded-as-code.csv": ("Account,Primary code,Key evidence\n7,uncoded: no evidence,\n"),
    "churn/quoted-comma.csv": (
        'Account,Dropdown,Primary code,Key evidence\n"Acme, Inc",Price,Champion left,\n'
    ),
    "churn/good.csv": (
        "Account,Dropdown,Primary code,Key evidence\n"
        '1,Price,Missing capability,"ticket 12: ""no SSO"""\n'
    ),
    "churn/multiline.csv": (
        "Account,Dropdown,Primary code,Key evidence\n"
        '1,Price,Missing capability,"line one\n, line two"\n'
    ),
    "churn/uncoded.csv": ("Account,Dropdown,Primary code,Key evidence\n1,Price,,\n2,Price,   ,\n"),
    "churn/plain.csv": "a,b\n1,\n",
    "churn/one-column.csv": "Account,Primary code\n1,Champion left\n",
    "notes/blank.csv": (
        "Account,Dropdown,Primary code,Key evidence\n1,Price,Missing capability,\n"
    ),
    "churns/blank.csv": (
        "Account,Dropdown,Primary code,Key evidence\n1,Price,Missing capability,\n"
    ),
    "churn/blank.txt": (
        "Account,Dropdown,Primary code,Key evidence\n1,Price,Missing capability,\n"
    ),
    "churn/dir.csv/.keep": "",
    "-x/churn/blank.csv": (
        "Account,Dropdown,Primary code,Key evidence\n1,Price,Missing capability,\n"
    ),
    "a=b/churn/blank.csv": (
        "Account,Dropdown,Primary code,Key evidence\n1,Price,Missing capability,\n"
    ),
    "reports/q3/churn/2026/blank.csv": (
        "Account,Dropdown,Primary code,Key evidence\n1,Price,Missing capability,\n"
    ),
    "churn/oversize.csv": CHURN_HEADER + "1,Price,Missing capability,x\n" * 45000,
    # mem: require-memory-request
    "jobs/good.sbatch": ("#!/bin/bash\n#SBATCH --job-name=x\n#SBATCH --mem=4G\necho hi\n"),
    "jobs/nomem.sbatch": ("#!/bin/bash\n#SBATCH --job-name=x\n#SBATCH --time=1:00:00\necho hi\n"),
    "slurm/nomem.sh": "#!/bin/bash\n#SBATCH --cpus-per-task=4\n",
    "ops/slurm/sub/nomem.sh": "#SBATCH --time=1\n",
    "-x/jobs/nomem.sbatch": "#SBATCH --time=1\n",
    "jobs/jobname.sbatch": "#SBATCH --job-name=--memory\n",
    "jobs/partition.sbatch": "#SBATCH -p gpu\n",
    "jobs/tab.sbatch": "#SBATCH\t--time=1\n",
    "jobs/crlf.sbatch": "#SBATCH --time=1\r\n#SBATCH --nodes=1\r\n",
    "jobs/body.sbatch": "#SBATCH --time=1\nsrun --mem=4G ./a.out\n",
    "jobs/memx.sbatch": "#SBATCH --memx=4G\n",
    "jobs/nospace.sbatch": "#SBATCH--mem=4G\n",
    "jobs/bind.sbatch": "#SBATCH --mem-bind=local\n#SBATCH --memory=3\n",
    "jobs/commented.sbatch": "##SBATCH --mem=4G\n#SBATCH --time=1\n",
    "slurm/sub/cpu.sh": "#SBATCH --mem-per-cpu 2G\n",
    "jobs/gpu.sbatch": "#SBATCH --mem-per-gpu=16G",
    "jobs/late-mem.sbatch": "#SBATCH --time=1\n#SBATCH --nodes=2\n#SBATCH --mem=0\n",
    "slurm/nodirective.sh": "echo hi\n",
    "myslurm/nomem.sh": "#SBATCH --time=1\n",
    "jobs/nomem.sh": "#SBATCH --time=1\n",
    "jobs/dir.sbatch/.keep": "",
    # lock: close-lock-date
    "books/2026-09-close.md": "# Close\nPeriod locked: yes, 2026-10-03\n",
    "books/bad-close.md": "# Close\nPeriod locked: yes\n",
    "books/bad-true-close.md": "# Close\n**Period locked:** true\n",
    "books/close-undated.md": "Period locked: yes, date\n",
    "books/close-placeholder.md": ("Period locked: [yes, YYYY-MM-DD]\nPeriod locked: yes/no\n"),
    "books/close-no.md": "Period locked: no\n",
    "books/close-written-date.md": (
        "Period locked: yes, 3 Oct 2026\nperiod locked: yes (Oct 3, 2026)\n"
        "Period locked: yes 03/10/2026\n"
    ),
    "books/close-second-line.md": ("Period locked: yes, 2026-10-03\nPeriod locked: yes\n"),
    "books/notes.md": "Period locked: yes\n",
    "books/close.csv": "Period locked: yes\n",
    "books/Month-CLOSE.MD": "Period locked: yes\n",
    "books/dir-close.md/.keep": "",
    "-x/close.md": "Period locked: yes\n",
    # dmap: drift-map-ignore-reason
    "dm/pass/drift-map.yaml": (
        "docs_root: docs/\nignore:\n  - id: timeout\n"
        "    reason: generic; mapped as storage.timeout\n  - id: name\n"
        '    reason: "too generic"\n  - id: x # why\n    reason: >\n      folded text\n'
        "  - {id: y, reason: z}\n"
    ),
    "dm/nextline/drift-map.yaml": ("ignore:\n  - id: a\n    reason:\n      generic key\n"),
    "dm/crlf/drift-map.yaml": "ignore:\r\n  - id: a\r\n    reason: generic\r\n",
    "dm/noignore/drift-map.yaml": ("docs_root: docs/\npaths:\n  - glob: a\n    pages: [b]\n"),
    "dm/emptylist/drift-map.yaml": "ignore: []\n",
    "dm/othersection/drift-map.yaml": (
        "ignore:\n  - id: timeout\n    reason: generic\npaths:\n  - glob: src/**\n"
        "    pages:\n      - docs/a.md\n"
    ),
    "dm/noreason/drift-map.yaml": ("ignore:\n  - id: timeout\n    reason: generic\n  - id: name\n"),
    "dm/noreason/notes.yaml": "ignore:\n  - id: name\n",
    "dm/noreason/drift-map.yml": "ignore:\n  - id: name\n",
    "dm/empty/drift-map.yaml": ("ignore:\n  - id: a\n    reason:\n  - id: b\n    reason: ok\n"),
    "dm/quoted/drift-map.yaml": 'ignore:\n  - id: a\n    reason: ""\n',
    "dm/null/drift-map.yaml": "ignore:\n  - id: a\n    reason: null\n",
    "dm/comment/drift-map.yaml": "ignore:\n  - id: a\n    reason: # todo\n",
    "dm/flow/drift-map.yaml": "ignore:\n  - {id: a, reason: ok}\n  - {id: b}\n",
    "dm/zero/drift-map.yaml": "ignore:\n- id: a\n- id: b\n  reason: ok\n",
    "dm/oversize/drift-map.yaml": "ignore:\n" + "a" * 1_100_000,
    "dm/dir/drift-map.yaml/.keep": "",
    # sleep: no-fixed-sleep-in-tests (every path under sl/ so no other hook's scratch file collides)
    "sl/web/x.test.js": "await sleep(5)\n",
    "sl/web/y.spec.ts": "await   sleep(5);\n",
    "sl/suite/foo_test.py": "time.sleep(1)\n",
    "sl/suite/test_crlf.py": "x = 1\r\ntime.sleep(1)\r\n",
    "sl/suite/test_tab.py": "def t():\n\ttime.sleep(1)\n",
    "sl/src/CapTest.java": "Thread.Sleep(5);\n",
    "sl/suite/test_many.py": "time.sleep(1)\n" * 8,
    "sl/src/main.go": "time.Sleep(1)\n",
    "sl/pkg/block_test.go": "/* time.Sleep(1) */\n",
    "sl/suite/test_bad.py": "import time\n\n\ndef test_x():\n    time.sleep(2)\n",
    "sl/pkg/bad_test.go": "package p\n\nfunc TestX(t *testing.T) {\n\ttime.Sleep(time.Second)\n}\n",
    "sl/src/BadTest.java": (
        "class BadTest {\n  void t() throws Exception { Thread.sleep(500); }\n}\n"
    ),
    "sl/web/app.test.ts": "it('x', async () => {\n  await sleep(100);\n});\n",
    "sl/tests/helper.py": "import time\ntime.sleep(1)\n",
    "sl/suite/test_late.py": "# time.sleep(9)\n\n    # time.sleep(9)\nx = 1\ntime.sleep(1)\n",
    "sl/suite/test_inline.py": "x = 1; time.sleep(1)\n",
    "-sl/suite/test_dash.py": "time.sleep(1)\n",
    "sl/suite/test_comment.py": "# time.sleep(1)\nx = 1\n",
    "sl/pkg/ok_test.go": "// time.Sleep(1)\n/*\n * Thread.sleep(1)\n */\n",
    "sl/suite/test_marked.py": "time.sleep(0.1)  # sleep-ok: backoff under test\n",
    "sl/suite/test_clean.py": "def test_x():\n    assert 1 == 1\n",
    "sl/suite/test_word.py": "# we do not sleep here\nname = 'sleeper'\n",
    "sl/src/app.py": "import time\ntime.sleep(1)\n",
    "sl/suite/test_data/x.py": "time.sleep(1)\n",
    "sl/tests/README.md": "Do not call time.sleep(1).\n",
    "sl/suite/test_bare.py": "from time import sleep\nsleep(1)\n",
    "sl/suite/test_dir.py/.keep": "",
    # wfrun: flag-untrusted-field-in-run
    ".github/workflows/title-in-run.yml": (
        "on: pull_request_target\n"
        "jobs:\n"
        "  a:\n"
        "    steps:\n"
        "      - name: t\n"
        "        run: |\n"
        '          echo "${{ github.event.pull_request.title }}"\n'
    ),
    ".github/workflows/head-ref-inline.yml": (
        "jobs:\n  a:\n    steps:\n      - run: echo ${{ github.head_ref }}\n"
    ),
    ".github/workflows/comment-in-script.yml": (
        "jobs:\n"
        "  a:\n"
        "    steps:\n"
        "      - uses: actions/github-script@v7\n"
        "        with:\n"
        "          script: |\n"
        "            const t = '${{ github.event.comment.body }}';\n"
    ),
    ".github/workflows/head-commit.yaml": (
        "jobs:\n"
        "  a:\n"
        "    steps:\n"
        "      - name: m\n"
        "        run: >-\n"
        "          echo ${{ github.event.head_commit.message }}\n"
    ),
    ".github/workflows/crlf-bad.yml": (
        "jobs:\r\n"
        "  a:\r\n"
        "    steps:\r\n"
        "      - run: |\r\n"
        "          echo ${{ github.event.issue.title }}\r\n"
    ),
    ".github/workflows/shell-comment-in-run.yml": (
        "jobs:\n"
        "  a:\n"
        "    steps:\n"
        "      - run: |\n"
        "          # ${{ github.event.pull_request.body }}\n"
        "          true\n"
    ),
    ".github/workflows/no-spaces.yml": (
        "jobs:\n"
        "  a:\n"
        "    steps:\n"
        "      - run: |\n"
        "          echo ${{github.event.pull_request.head.ref}}\n"
    ),
    ".github/workflows/second-step-bad.yml": (
        "jobs:\n"
        "  a:\n"
        "    steps:\n"
        "      - run: echo ${{ github.sha }}\n"
        "      - run: |\n"
        "          echo ok\n"
        "          git checkout ${{ github.event.pull_request.head.label }} x\n"
    ),
    "-x/.github/workflows/bad.yml": (
        "jobs:\n  a:\n    steps:\n      - run: echo ${{ github.head_ref }}\n"
    ),
    ".github/workflows/env-carried.yml": (
        "jobs:\n"
        "  a:\n"
        "    steps:\n"
        "      - name: t\n"
        "        env:\n"
        "          T: ${{ github.event.pull_request.title }}\n"
        "        run: |\n"
        '          echo "$T"\n'
    ),
    ".github/workflows/safe-expression.yml": (
        "jobs:\n  a:\n    steps:\n      - run: echo ${{ github.sha }} ${{ github.run_id }}\n"
    ),
    ".github/workflows/comment-outside-block.yml": (
        "jobs:\n  a:\n    steps:\n      # run: echo ${{ github.head_ref }}\n      - run: echo ok\n"
    ),
    ".github/workflows/condition-not-block.yml": (
        "jobs:\n"
        "  a:\n"
        "    if: ${{ github.event.pull_request.title != '' }}\n"
        "    steps:\n"
        "      - run: |\n"
        "          echo ok\n"
        "        name: ${{ github.head_ref }}\n"
    ),
    ".github/workflows/with-not-script.yml": (
        "jobs:\n"
        "  a:\n"
        "    steps:\n"
        "      - uses: actions/checkout@v4\n"
        "        with:\n"
        "          ref: ${{ github.head_ref }}\n"
    ),
    ".github/workflows/no-expression.yml": ("jobs:\n  a:\n    steps:\n      - run: echo hi\n"),
    ".github/workflows/sub/nested.yml": (
        "jobs:\n  a:\n    steps:\n      - run: echo ${{ github.head_ref }}\n"
    ),
    "other/title-in-run.yml": (
        "jobs:\n  a:\n    steps:\n      - run: echo ${{ github.head_ref }}\n"
    ),
    ".github/workflows/title-in-run.txt": (
        "jobs:\n  a:\n    steps:\n      - run: echo ${{ github.head_ref }}\n"
    ),
    ".github/workflows/dir.yml/.keep": "",
    ".github/workflows/mixed-case.yml": WF_STEPS
    + "      - run: echo ${{ github.event.Pull_Request.TITLE }}\n",
    ".github/workflows/commit-email.yml": WF_STEPS
    + "      - run: echo ${{ github.event.commits[0].author.email }}\n",
    ".github/workflows/commit-name.yml": WF_STEPS
    + '      - run: |\n          echo "${{ github.event.commits[*].author.name }}"\n',
    ".github/workflows/head-email.yml": WF_STEPS
    + "      - run: echo ${{ github.event.head_commit.author.EMAIL }}\n",
    ".github/workflows/commit-message.yml": WF_STEPS
    + "      - run: echo ${{ github.event.commits[1].message }}\n",
    ".github/workflows/page-name.yml": WF_STEPS
    + "      - run: echo ${{ github.event.pages[0].page_name }}\n",
    ".github/workflows/repo-description.yml": WF_STEPS
    + "      - run: echo ${{ github.event.pull_request.head.repo.description }}\n",
    ".github/workflows/commit-id.yml": WF_STEPS
    + "      - run: echo ${{ github.event.commits[0].id }}"
    + " ${{ github.event.commits[0].author.username }}\n",
    ".github/workflows/commit-email-env.yml": WF_STEPS
    + "      - env:\n          E: ${{ github.event.commits[0].author.email }}\n"
    + '        run: echo "$E"\n',
    ".github/workflows/commits-filter-message.yml": WF_STEPS
    + "      - run: echo ${{ join(github.event.commits.*.message, ' ') }}\n",
    ".github/workflows/commits-filter-email.yml": WF_STEPS
    + "      - run: echo ${{ github.event.commits.*.author.email }}\n",
    ".github/workflows/pages-filter-name.yml": WF_STEPS
    + "      - run: echo ${{ join(github.event.pages.*.page_name) }}\n",
    ".github/workflows/commits-filter-id.yml": WF_STEPS
    + "      - run: echo ${{ github.event.commits.*.id }}\n",
    # css: flag-viewport-width-css
    "css/bad.css": ".hero {\n  width: 100vw;\n}\n",
    "css/bad-min.css": ".a {\n  min-width: 100dvw !important;\n}\n",
    "css/bad-max.css": ".a { max-width:100svw }\n",
    "css/bad-minified.css": ".a{color:red}.b{border-width:2px;width:100vw}.c{top:0}\n",
    "-x/css/bad.css": ".a{width:100vw}\n",
    "css/bad-upper.css": ".A { WIDTH: 100VW; }\r\n",
    "css/bad-late.css": ".a{width:100%}\n.b{line-width:100vw}\n.c{\n  width: 100vw;\n}\n",
    "css/oversize.css": ".a{color:red}\n" * 81000,
    "css/ok.css": ".a{width:100%}\n.b{max-width:60rem}\n",
    "css/ok-calc.css": (
        ".a{width:calc(100vw - 2rem)}\n.b{line-width:100vw}\n"
        ".c{width:min(100vw,60rem)}\n.d{width:100vw-ish}\n"
    ),
    "css/bleed.css": ".band{width:100vw;margin-left:calc(50% - 50vw)}\n",
    "css/notes.txt": ".a{width:100vw}\n",
    "css/dir.css/keep.txt": "x\n",
    # slice: slice-waiver-placement
    "docs/slices/w-bad/plan.md": (
        "First question: which step can be shown working first?\n\n# Plan: w\n"
        "\n## Waiver\nReason: x\n"
    ),
    "docs/slices/w-bad/frame.md": "x\n## Waiver\nReason: x\n",
    "docs/slices/w-bad/inspect.md": "x\n## Waiver\n",
    "docs/slices/w-bad/yield.md": "x\n\n\n## Waiver\n",
    "docs/slices/w-crlf/plan.md": "x\r\n## Waiver\r\n",
    "docs/slices/w-trail/plan.md": "x\n## Waiver \t\n",
    "docs/slices/-x/plan.md": "## Waiver\n",
    "docs/slices/w-second/plan.md": "## Waiverish\n## Waiver\n",
    "docs/slices/w-ok/decision.md": "x\n## Waiver\nReason: x\n",
    "docs/slices/w-ok/launch.md": "x\n## Waiver\nReason: x\n",
    "docs/slices/w-ok/plan.md": "First question: x\n\n## Steps\n\n1. a\n",
    "docs/slices/w-h3/plan.md": "### Waiver\n",
    "docs/slices/w-lookalike/plan.md": "## Waived\n## Waivers\n## waiver\n  ## Waiver\n",
    "docs/slices/w-ok/notes.md": "## Waiver\nReason: x\n",
    "docs/slices/w-ok/deep/plan.md": "## Waiver\nReason: x\n",
    "mydocs/slices/w-ok/plan.md": "## Waiver\nReason: x\n",
    "docs/slices/w-dir/plan.md/.keep": "",
    "docs/slices/w-empty/plan.md": "",
    # adr: require-considered-options
    "docs/decisions/0003-one.md": "## Considered Options\n\n* only one\n\n## Decision Outcome\n",
    "docs/decisions/0004-none.md": "# T\n\n## Context and Problem Statement\nx\n",
    "docs/decisions/0007-table.md": "## Considered Options\n| a | b |\n",
    "docs/decisions/0008-empty.md": "",
    "docs/decisions/sub/0012-nested-one.md": "## Considered Options\n- a\n## Other\n* b\n* c\n",
    "docs/adr/ADR-0013-one.md": "## Considered Options\n1. a\n",
    "docs/decisions/0014-indented.md": "## Considered Options\n  * a\n  * b\n",
    "docs/decisions/0015-crlf-one.md": "## Considered Options\r\n* a\r\n",
    "-x/docs/decisions/0016-one.md": "## Considered Options\n* a\n",
    "docs/decisions/0001-good.md": "## Considered Options\n\n* a\n* b\n\n## Decision Outcome\n",
    "docs/decisions/0002-numbered.md": "## Considered Options\n1. a\n2. b\n",
    "docs/adr/0005-crlf.md": "## Considered Options\r\n- a\r\n- b\r\n",
    "docs/decisions/0006-subheading.md": "## Considered Options\n* a\n### Notes\n* b\n",
    "docs/decisions/README.md": "## Considered Options\n",
    "mydocs/decisions/0009-one.md": "## Considered Options\n* a\n",
    "docs/decisions/notes.md": "# Notes\n",
    "docs/decisions/0017-dir.md/.keep": "",
    # rbk: runbook-stamp
    "runbooks/good.md": (
        "# Runbook: checkout errors\n\n"
        "**Owner:** platform-oncall · **Last verified:** 2026-03-14 by oncall during a game day\n"
    ),
    "runbooks/two-line.md": (
        "# Runbook: queue\n\n**Owner:** sre rota\n"
        "**Last verified:** 2026-03-14 by sre during a drill\n"
    ),
    "runbooks/colon-outside.md": "# Runbook\n**Owner**: sre\n**Last verified**: 2026-03-14\n",
    "ops/db-runbook.md": "# Runbook\n- Owner: dba rota\n- Last verified: 2026-03-14\n",
    "runbooks/crlf.md": "# Runbook\r\nOwner: sre\r\nLast verified: 2026-03-14\r\n",
    "runbooks/-n.md": "Owner: sre\nLast verified: 2026-03-14\n",
    "runbooks/placeholder.md": (
        "# Runbook\n**Owner:** [team or rota]\n**Last verified:** [YYYY-MM-DD] by [rota]\n"
    ),
    "runbooks/no-owner.md": "# Runbook\nLast verified: 2026-03-14\n",
    "runbooks/no-date.md": "# Runbook\nOwner: sre\n",
    "runbooks/bad-month.md": "# Runbook\nOwner: sre\nLast verified: 2026-13-01\n",
    "runbooks/future.md": "# Runbook\nOwner: sre\nLast verified: 2999-01-01\n",
    "runbooks/fenced.md": "# Runbook\n```\nOwner: sre\nLast verified: 2026-03-14\n```\n",
    "runbooks/late-stamp.md": "x\n" * 45 + "Owner: sre\nLast verified: 2026-03-14\n",
    "runbooks/co-owner.md": "Co-Owner: sre\nLast verified: 2026-03-14\n",
    "runbooks/long-date.md": "Owner: sre\nLast verified: 2026-03-145\n",
    "runbooks/owner-empty.md": "Owner:\nLast verified: 2026-03-14\n",
    "runbooks/empty.md": "",
    "-x/runbooks/bad.md": "# Runbook\n",
    "runbooks/README.md": "# Runbooks\n",
    "runbooks/index.md": "# Index\n",
    "ops-notes/other.md": "# Notes\n",
    "myrunbooks/bad.md": "# Notes\n",
    "runbooks/notes.txt": "# Notes\n",
    "runbooks/dir.md/.keep": "",
    "runbook-verification-record.md": RBK_RECORD,
    "runbooks/verifications/2026-03-14-checkout.md": RBK_RECORD,
    "runbooks/2026-03-14-checkout.md": RBK_RECORD,
    "runbooks/db-verification-record.md": "# Notes\n",
    "runbooks/late-heading.md": "# Runbook\n\n# Runbook verification record\n",
    # wkrev: weekly-review-shape
    "wk/reviews/two.md": (
        "# Week of 5 Jan\n\n## Commitments (3-5)\n1. a\n2. b\n\n"
        "## Consciously not doing\n- x - y - 2026-12-01\n"
    ),
    "wk/reviews/six.md": (
        "# Week of 5 Jan\n\n## Commitments (3-5)\n1. item\n2. item\n3. item\n"
        "4. item\n5. item\n6. item\n\n## Consciously not doing\n"
        "- x - y - 2026-12-01\n"
    ),
    "wk/reviews/2026/six-bullets.md": (
        "# Week of 5 Jan\n\n## Commitments (3-5)\n- a\n- a\n- a\n- a\n- a\n"
        "- a\n\n## Consciously not doing\n- x - y - 2026-12-01\n"
    ),
    "wk/reviews/no-not-doing.md": "# Week of 5 Jan\n\n## Commitments (3-5)\n1. a\n2. b\n3. c\n",
    "wk/reviews/no-commitments.md": (
        "# Week of 5 Jan\n\n## Consciously not doing\n- x - y - 2026-12-01\n"
    ),
    "wk/reviews/empty-commitments.md": (
        "# Week of 5 Jan\n\n## Commitments (3-5)\n\n## Consciously not doing\n"
        "- x - y - 2026-12-01\n"
    ),
    "-wk/reviews/bad.md": (
        "# Week of 5 Jan\n\n## Commitments (3-5)\n1. a\n\n"
        "## Consciously not doing\n- x - y - 2026-12-01\n"
    ),
    "reviews/root-bad.md": (
        "# Week of 5 Jan\n\n## Commitments (3-5)\n1. a\n\n"
        "## Consciously not doing\n- x - y - 2026-12-01\n"
    ),
    "wk/reviews/after-section.md": (
        "# Week of 5 Jan\n## Commitments\n1. a\n2. b\n"
        "## Consciously not doing\n- x - y - 2026-12-01\n- p\n- q\n- r\n"
    ),
    "wk/reviews/five.md": (
        "# Week of 5 Jan\n\n## Commitments (3-5)\n1. item\n2. item\n3. item\n"
        "4. item\n5. item\n\n## Consciously not doing\n- x - y - 2026-12-01\n"
    ),
    "wk/reviews/crlf.md": (
        "# Week of 5 Jan\r\n## Commitments\r\n- a\r\n- b\r\n- c\r\n"
        "## Consciously not doing\r\n- x\r\n"
    ),
    "wk/reviews/blank-first.md": (
        "\n\n# Week of 5 Jan\n\n## Commitments (3-5)\n1. a\n2. b\n3. c\n\n"
        "## Consciously not doing\n- x - y - 2026-12-01\n"
    ),
    "wk/reviews/month.md": "# Month review\n## Commitments\n- a\n",
    "wk/reviews/notes.md": "Notes\n## Commitments\n- a\n",
    "wk/myreviews/six.md": (
        "# Week of 5 Jan\n\n## Commitments (3-5)\n- a\n- a\n- a\n- a\n- a\n"
        "- a\n\n## Consciously not doing\n- x - y - 2026-12-01\n"
    ),
    "wk/reviews/six.txt": (
        "# Week of 5 Jan\n\n## Commitments (3-5)\n- a\n- a\n- a\n- a\n- a\n"
        "- a\n\n## Consciously not doing\n- x - y - 2026-12-01\n"
    ),
    "wk/reviews/dir.md/.keep": "",
    # tlsoff: tls-verification-off
    "cfg/kube.yaml": (
        "clusters:\n- cluster:\n    server: https://k.example\n    insecure-skip-tls-verify: true\n"
    ),
    "cfg/client.json": '{"a": {"insecure_skip_verify": "true"}}\n',
    "cfg/app.ini": "[x]\nverify_ssl = false # temporary\n",
    "cfg/play.yml": "- uri:\n    validate_certs: no\n",
    "cfg/crlf.conf": "ssl_verify=0\r\n",
    "cfg/oversize.json": "x" * (1024 * 1024 + 1),
    "cfg/commented.yaml": (
        "# insecure-skip-tls-verify: true\n; verify_ssl = false\n// ssl_verify: false\n"
    ),
    "cfg/good.yaml": (
        "insecure-skip-tls-verify: false\nverify_ssl: true\n"
        "my_ssl_verify: false2\nnot_skip_tls_verify_x: 1\n"
    ),
    "cfg/exception.yaml": "validate_certs: false # tls-exception TLS-12\n",
    "sl/suite/test_token.py": (
        "import time\n\n\ndef test_x():\n    time.sleep(2)  # FAKE-TOKEN-0000\n"
    ),
    ".github/workflows/token-in-run.yml": WF_STEPS
    + "      - run: echo ${{ github.head_ref }} FAKE-TOKEN-0000\n",
    "css/token.css": ".hero { width: 100vw; } /* FAKE-TOKEN-0000 */\n",
    "cfg/token.yaml": "insecure-skip-tls-verify: true # FAKE-TOKEN-0000\n",
    "cfg/kube.txt": "insecure-skip-tls-verify: true\n",
    "cfg/camel-insecure.json": '{"insecureSkipVerify": true}\n',
    "cfg/camel-insecure-tls.yaml": "insecureSkipTLSVerify: true\n",
    "cfg/camel-skip-tls.yaml": "skipTLSVerify: yes\n",
    "cfg/camel-tls-skip.yaml": "tlsSkipVerify: true\n",
    "cfg/vault.conf": 'tls_skip_verify = "true"\n',
    "cfg/yum.conf": "[main]\nsslverify=0\n",
    "cfg/gitconfig.ini": "[http]\n\tsslVerify = false\n",
    "cfg/npm.ini": "strict-ssl=false\n",
    "cfg/node.json": '{"rejectUnauthorized": false}\n',
    "cfg/verify-true.ini": "verify_ssl: true\n",
    "cfg/yum-ok.conf": "[main]\nsslverify=1\n",
    "cfg/npm-ok.ini": "strict-ssl=true\n",
    "cfg/node-ok.json": '{"rejectUnauthorized": true}\n',
    "cfg/bare-verify.yaml": "verify: false\ninsecure: true\n",
}


def _path_for(tool):
    found = shutil.which(tool)
    if tool == "python3" and found is None:
        import sys

        found = sys.executable
    return found


def _missing(tools):
    return [t for t in tools if _path_for(t) is None]


_ALL_TOOLS = (*BASE_TOOLS, *(t for extra in EXTRA_TOOLS.values() for t in extra))
pytestmark = pytest.mark.skipif(
    bool(_missing(_ALL_TOOLS)), reason=f"needs {', '.join(_missing(_ALL_TOOLS))} on PATH"
)


@pytest.fixture(scope="session")
def scratch(tmp_path_factory):
    cwd = tmp_path_factory.mktemp("kit-hook-cwd")
    for name, text in SCRATCH_FILES.items():
        target = cwd / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    (cwd / "timing").mkdir()
    return cwd


NORMALISING = ("tf", "kill", "sym", "erase", "ddl")


@pytest.fixture(scope="session")
def bins(tmp_path_factory):
    """One directory of symlinks per parser mode and hook, holding exactly the tools that hook
    may use: the base tools, its parser and whatever EXTRA_TOOLS grants it."""
    made = {}
    for mode, parser in MODES.items():
        if _missing(parser):
            continue
        made[mode] = {}
        for key in HOOK_FILES:
            directory = tmp_path_factory.mktemp(f"bin-{mode}-{key}")
            for tool in (*BASE_TOOLS, *EXTRA_TOOLS.get(key, ()), *parser):
                (directory / tool).symlink_to(_path_for(tool))
            made[mode][key] = directory
    return made


@pytest.fixture(scope="session")
def noawk_bins(tmp_path_factory):
    """Like `bins`, for the hooks that normalise the command with awk, but with no awk."""
    made = {}
    for mode, parser in MODES.items():
        if _missing(parser):
            continue
        made[mode] = {}
        for key in NORMALISING:
            directory = tmp_path_factory.mktemp(f"bin-noawk-{mode}-{key}")
            for tool in (*(t for t in BASE_TOOLS if t != "awk"), *parser):
                (directory / tool).symlink_to(_path_for(tool))
            made[mode][key] = directory
    return made


def _hook_path(key):
    found = sorted(ROOT.glob(f"plugins/*/skills/*/assets/hooks/{HOOK_FILES[key]}.sh"))
    assert len(found) == 1, key
    return found[0]


def _expand(value):
    """Rebuild a large string from `{"parts": [text, [unit, count], ...]}`."""
    if isinstance(value, dict) and "parts" in value:
        return "".join(p if isinstance(p, str) else p[0] * p[1] for p in value["parts"])
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def run_hook(key, stdin, mode, bins, scratch, timeout):
    if mode not in bins:
        pytest.skip(f"the {mode} parser mode needs {' and '.join(MODES[mode])} on PATH")
    marker = scratch / "STUB_JSON_RAN"
    marker.unlink(missing_ok=True)
    env = {"PATH": str(bins[mode][key]), "LANG": "C.UTF-8", "HOME": str(scratch)}
    try:
        done = subprocess.run(  # noqa: S603
            [_path_for("bash"), str(_hook_path(key))],
            input=stdin,
            capture_output=True,
            cwd=scratch,
            env=env,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail(
            f"{HOOK_FILES[key]} ({mode}) did not finish in {timeout} s; "
            "a hook that outlasts its timeout fails open"
        )
    assert not marker.exists(), "the hook imported json.py from the working directory"
    return done


# The cost budget for one hook run is measured in CPU time, not wall time: the suite runs the
# timing cases on every core at once, and a run that waits for a free core is slow without the hook
# doing more work. CPU speed still differs between machines (one CI runner spent 7.2 CPU s on a
# case that costs 1.4 on a development machine), so the budget is the larger of CPU_BUDGET and
# BASELINE_FACTOR times what the same hook spends, on the same machine, on a neutral payload of the
# same size, capped at CPU_CEILING. The cap keeps a uniformly slow linear hook from being budgeted
# to the edge of HOOK_TIMEOUT, past which it fails open. Every linear timing case costs at most
# 2.4 times its baseline; the quadratic erase hook
# of 08c7086 cost 79 times it on descriptor-copies-128k, so a factor of 8 separates the two on any
# machine for a slowdown that depends on the payload.
#
# A slowdown that does not depend on the payload, such as a loop over the command's length, slows
# the neutral baseline in step and so raises its own budget. That is the one case the factor cannot
# see, so whenever BASELINE_FACTOR times the baseline exceeds CPU_BUDGET (a hook that slow is the
# only one whose budget the baseline decides), the hook is also run on the neutral payload at a
# quarter of the size, and the two must grow by less than GROWTH_LIMIT. Linear growth is about 4
# even with start-up cost, and quadratic is about 16. Growth with a power about 1.5 or
# below (a ratio under GROWTH_LIMIT for four times the input) is not caught; the
# check separates linear from quadratic and does not prove linearity. HOOK_TIMEOUT is Claude
# Code's default hook timeout: a run past it fails open, so it is the wall-clock limit for a hang.
CPU_BUDGET = 5
BASELINE_FACTOR = 8
GROWTH_LIMIT = 8
HOOK_TIMEOUT = 60
CPU_CEILING = HOOK_TIMEOUT / 2
NEUTRAL_LINE = "echo ok\n"
NEUTRAL_KEYS = ("command", "content", "new_string")


def run_hook_timed(key, stdin, mode, bins, scratch):
    """Run a hook and return it with the CPU seconds it and its children spent."""
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    done = run_hook(key, stdin, mode, bins, scratch, timeout=HOOK_TIMEOUT)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    spent = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    return done, spent


def _neutral(tool_input, divisor=1):
    """The same payload with each text field replaced by harmless lines of 1/divisor the length."""
    out = dict(tool_input)
    for name in NEUTRAL_KEYS:
        if isinstance(out.get(name), str):
            size = len(out[name]) // divisor
            out[name] = (NEUTRAL_LINE * (size // len(NEUTRAL_LINE) + 1))[:size]
    return out


def _neutral_stdin(tool_input, divisor=1):
    payload = {"tool_input": _neutral(tool_input, divisor)}
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


_BASELINES = {}
_GROWTH = {}


def cpu_budget(key, tool_input, mode, bins, scratch):
    """CPU seconds a hook may spend on tool_input on this machine."""
    stdin = _neutral_stdin(tool_input)
    # The long-run cases share one neutral payload per hook and mode, so it is measured once.
    cache = (key, mode, stdin)
    if cache not in _BASELINES:
        _BASELINES[cache] = run_hook_timed(key, stdin, mode, bins, scratch)[1]
    baseline = _BASELINES[cache]
    if BASELINE_FACTOR * baseline > CPU_BUDGET:
        # The baseline now decides the budget, so check that it is not itself super-linear.
        if cache not in _GROWTH:
            quarter = run_hook_timed(key, _neutral_stdin(tool_input, 4), mode, bins, scratch)[1]
            _GROWTH[cache] = baseline / max(quarter, 0.01)
        growth = _GROWTH[cache]
        assert growth < GROWTH_LIMIT, (
            f"{HOOK_FILES[key]} ({mode}) grows {growth:.1f} times in CPU time for four times the "
            f"input on a neutral payload ({baseline:.1f} CPU s); linear is about 4, quadratic 16"
        )
    return min(CPU_CEILING, max(CPU_BUDGET, BASELINE_FACTOR * baseline))


def _stdin(case):
    if "raw" in case:
        return case["raw"].encode("utf-8")
    return json.dumps(_expand(case["payload"]), ensure_ascii=False).encode("utf-8")


def _case_id(case):
    return f"{case['hook']}-{case['name']}"


def test_the_table_covers_every_hook_and_names_are_unique():
    assert set(HOOK_FILES) == {c["hook"] for c in TABLE}
    assert len({_case_id(c) for c in TABLE}) == len(TABLE)
    on_disk = {p.stem for p in ROOT.glob("plugins/*/skills/*/assets/hooks/*.sh")}
    assert on_disk == set(HOOK_FILES.values())


def test_extra_tools_stay_with_the_hook_that_needs_them(bins):
    assert set(EXTRA_TOOLS) <= set(HOOK_FILES)
    for per_hook in bins.values():
        for key, directory in per_hook.items():
            for tool in {t for extra in EXTRA_TOOLS.values() for t in extra}:
                granted = tool in EXTRA_TOOLS.get(key, ())
                assert (directory / tool).exists() == granted, (key, tool)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("case", TABLE, ids=_case_id)
def test_hook_verdict(case, mode, bins, scratch):
    done = run_hook(case["hook"], _stdin(case), mode, bins, scratch, timeout=30)
    assert done.returncode == case["exit"], done.stderr.decode("utf-8", "replace")[:300]
    # Content the model did not write must not reach the feedback channel: a finding names
    # path:line and a fixed message, never the matched text.
    if "no_echo" in case:
        assert case["no_echo"].encode() not in done.stderr
    if case["exit"] == 2:
        assert (
            done.stderr.startswith(b"blocked")
            or b"placeholder" in done.stderr.lower()
            or b"invalid JSON" in done.stderr
        )


def _wild_cpu(scratch, mode, bins, repeats):
    rel = ".github/workflows/grow.yml"
    target = scratch / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "      - run: echo ${{ github.sha " + WILD_PREFIX * repeats + "\n", encoding="utf-8"
    )
    stdin = json.dumps({"tool_input": {"file_path": rel}}).encode("utf-8")
    done, spent = run_hook_timed("wfrun", stdin, mode, bins, scratch)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")[:300]
    return spent


@pytest.mark.parametrize("mode", MODES)
def test_the_wildcard_scan_grows_linearly(mode, bins, scratch):
    """A repeated index-form prefix with no closing bracket is the worst case for the scan. It
    stays inside CPU_BUDGET even when quadratic, so the budget row cannot tell the two apart;
    comparing a quarter of the input with the whole can (linear is about 4, quadratic 16)."""
    if mode not in bins:
        pytest.skip(f"the {mode} parser mode needs {' and '.join(MODES[mode])} on PATH")
    small = _wild_cpu(scratch, mode, bins, 12000)
    large = _wild_cpu(scratch, mode, bins, 48000)
    assert large / max(small, 0.05) < GROWTH_LIMIT, (small, large)


# Without awk the normalising hooks cannot read the command. Left alone they would exit 127,
# which is not a block, so the command would run unjudged; they refuse with exit 2 instead,
# whatever the command is.
NO_AWK_COMMANDS = {
    "tf": ("terraform apply -auto-approve", "terraform plan"),
    "kill": ("select pg_terminate_backend(pid)", "select 1"),
    "sym": ("rm App.dSYM", "ls build"),
    "erase": ("st-flash erase", "ls build"),
    "ddl": ("DROP TABLE t", "select 1"),
}


def test_no_awk_case_for_every_normalising_hook():
    assert set(NO_AWK_COMMANDS) == set(NORMALISING)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    ("key", "command"),
    [(k, c) for k in NORMALISING for c in NO_AWK_COMMANDS[k]],
    ids=lambda v: v if v in NORMALISING else v.replace(" ", "_"),
)
def test_a_missing_awk_refuses(key, command, mode, noawk_bins, scratch):
    if mode not in noawk_bins:
        pytest.skip(f"the {mode} parser mode needs {' and '.join(MODES[mode])} on PATH")
    assert not (noawk_bins[mode][key] / "awk").exists()
    stdin = json.dumps({"tool_input": {"command": command}}).encode("utf-8")
    done = run_hook(key, stdin, mode, noawk_bins, scratch, timeout=30)
    assert done.returncode == 2, done.stderr.decode("utf-8", "replace")[:300]
    assert done.stderr.startswith(b"blocked")
    assert b"awk" in done.stderr


# A call with no command to judge (a tool other than Bash, or a null command) must not fail for
# want of awk: the guard above is for a command that would run unjudged, and there is none.
@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("key", NORMALISING)
@pytest.mark.parametrize(
    "payload",
    [{"tool_input": {"command": None}}, {"tool_input": {}}, {}, {"tool_input": {"command": ""}}],
    ids=["null-command", "no-command", "no-tool-input", "empty-command"],
)
def test_no_command_is_allowed_without_awk(key, payload, mode, noawk_bins, scratch):
    if mode not in noawk_bins:
        pytest.skip(f"the {mode} parser mode needs {' and '.join(MODES[mode])} on PATH")
    done = run_hook(key, json.dumps(payload).encode("utf-8"), mode, noawk_bins, scratch, timeout=30)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")[:300]


@pytest.mark.parametrize("mode", MODES)
def test_a_missing_awk_is_named_by_the_suppression_hook(mode, tmp_path):
    """require-suppression-reason runs awk on the text itself. Without awk that is status 127, which
    is not a full disk; the message must say awk is missing and not send the reader to the
    temporary directory."""
    if _missing(MODES[mode]):
        pytest.skip(f"the {mode} parser mode needs {' and '.join(MODES[mode])} on PATH")
    directory = tmp_path / "bin"
    directory.mkdir()
    for tool in (*(t for t in BASE_TOOLS if t != "awk"), *MODES[mode]):
        (directory / tool).symlink_to(_path_for(tool))
    stdin = json.dumps(
        {"tool_input": {"file_path": "a.py", "content": "x = 1  # pragma: no mutate\n"}}
    ).encode("utf-8")
    done = run_hook("sup", stdin, mode, {mode: {"sup": directory}}, tmp_path, timeout=30)
    assert done.returncode == 2, done.stderr.decode("utf-8", "replace")[:300]
    # bash itself reports the missing command first, so the hook's own line is not the first.
    assert b"blocked: awk is not installed" in done.stderr
    assert b"free space" not in done.stderr


def _function_body(path, name):
    text = path.read_text("utf-8")
    start = text.index(f"\n{name}() {{\n") + 1
    return text[start : text.index("\n}\n", start) + 3]


def test_the_normalise_function_is_the_same_in_every_hook_that_has_one():
    bodies = {key: _function_body(_hook_path(key), "normalise") for key in NORMALISING}
    assert len(set(bodies.values())) == 1, {k: v for k, v in bodies.items()}
    assert "LC_ALL=C awk" in bodies["tf"]


def _awk_program(body):
    return body.split("awk '")[1].split("'")[0]


def test_the_terraform_hook_joins_lines_with_the_same_program_as_normalise():
    path = _hook_path("tf")
    assert _awk_program(_function_body(path, "join_lines")) == _awk_program(
        _function_body(path, "normalise")
    )


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # No # at the start of a word: one joined reading, as before.
        ("terraform plan \\\n-out=tfplan\n", "terraform plan -out=tfplan\n"),
        ("a\\\\\nb\n", "a\nb\n"),
        # A comment line ending in a backslash is not joined by bash, a quoted # is: both readings.
        ("#\\\nx\n", "#x\n#\nx\n"),
        ("echo 'a # b' \\\nls\n", "echo a # b ls\necho a # b \nls\n"),
        ("echo hi;#x\\\nrm\n", "echo hi;#xrm\necho hi;#x\nrm\n"),
        # The # inside a word is no comment, so the join stays certain.
        ("a#b \\\nc\n", "a#b c\n"),
    ],
)
def test_normalise_reads_both_ways_only_where_a_hash_makes_the_join_uncertain(text, expected):
    body = _function_body(_hook_path("tf"), "normalise")
    done = subprocess.run(  # noqa: S603
        [_path_for("bash"), "-c", body + 'printf "%s" "$1" | normalise', "bash", text],
        capture_output=True,
        text=True,
        check=True,
    )
    assert done.stdout == expected


def test_openocd_erase_address_is_refused_as_a_range_not_a_whole_device(bins, scratch):
    command = "openocd -c 'flash erase_address 0x08000000 0x100000'"
    stdin = json.dumps({"tool_input": {"command": command}}).encode("utf-8")
    for mode in MODES:
        done = run_hook("erase", stdin, mode, bins, scratch, timeout=30)
        assert done.returncode == 2
        assert b"erase_address" in done.stderr
        assert b"range" in done.stderr
        assert b"whole-device" not in done.stderr


# Worst-case inputs of about 2 MB, built here because they are too large for the table. Each
# is (name, builder, expected exit, files the working directory must hold).
MB = 1_000_000
# A schema of thousands of small objects, closed and open, for the closed-object hook.
_CLOSED_OBJECT = '"p{}":{{"type":"object","properties":{{}},"additionalProperties":false}}'
_OPEN_OBJECT = '"p{}":{{"type":"object","properties":{{}}}}'
CLOSED_BIG = (
    '{"type":"object","properties":{'
    + ",".join(_CLOSED_OBJECT.format(i) for i in range(8000))
    + '},"additionalProperties":false}'
)
OPEN_BIG = (
    '{"type":"object","properties":{'
    + ",".join(_OPEN_OBJECT.format(i) for i in range(8000))
    + '},"additionalProperties":false}'
)
# The text the index-form entries of flag-untrusted-field-in-run look for before a bracket.
WILD_PREFIX = "github.event.commits["

BIG = {
    "tf": [
        # A command made of continuation lines is joined into one line; joining by appending to a
        # buffer is quadratic in the number of lines.
        ("continuation-lines", lambda: {"command": "terraform plan \\\n" * 100000}, 2, {}),
        ("one-huge-token", lambda: {"command": "terraform apply " + "x" * (2 * MB)}, 2, {}),
        ("quote-run", lambda: {"command": "terraform apply " + "'" * (2 * MB)}, 2, {}),
        ("many-terraformer-words", lambda: {"command": "terraformer " * 170000}, 0, {}),
        ("no-terraform", lambda: {"command": "echo " + "y" * (2 * MB)}, 0, {}),
    ],
    "kill": [
        ("continuation-lines", lambda: {"command": "echo \\\n" * 300000}, 0, {}),
        (
            "huge-first-argument",
            lambda: {"command": "pg_terminate_backend(" + "x" * (2 * MB)},
            2,
            {},
        ),
        (
            "half-mib-first-argument",
            lambda: {"command": "pg_terminate_backend(" + "x" * 524288 + ")"},
            2,
            {},
        ),
        ("many-calls", lambda: {"command": "select pg_terminate_backend(1);" * 70000}, 2, {}),
        ("name-without-paren", lambda: {"command": "pg_terminate_backend " * 95000}, 2, {}),
        ("no-function", lambda: {"command": "echo " + "x" * (2 * MB)}, 0, {}),
    ],
    # Each stays under the 1 MiB the hook refuses at, so the time is the awk pass over the text and
    # not the refusal; test_the_sup_timing_rows_reach_the_awk_pass checks that.
    "sup": [
        (
            "many-reasoned-markers",
            lambda: {
                "file_path": "a.py",
                "content": "x = 1  # pragma: no mutate because ok\n" * 25000,
            },
            0,
            {},
        ),
        (
            "many-bare-markers",
            lambda: {"file_path": "a.py", "content": "x = 1  # pragma: no mutate\n" * 36000},
            2,
            {},
        ),
        (
            "one-long-marker-line",
            lambda: {
                "file_path": "a.py",
                "content": "x = 1 " + "y" * 900000 + " # pragma: no mutate",
            },
            2,
            {},
        ),
        (
            "many-stryker-markers",
            lambda: {
                "file_path": "a.ts",
                "content": "// Stryker disable next-line all: ok\n" * 27000,
            },
            0,
            {},
        ),
        (
            "many-multibyte-reasons",
            lambda: {
                "file_path": "a.py",
                "content": "x = 1  # pragma: no mutate \u7b49\u4fa1\u5909\u7570 \u2026\n" * 20000,
            },
            0,
            {},
        ),
        (
            "oversized-refusal",
            lambda: {
                "file_path": "a.py",
                "content": "x = 1  # pragma: no mutate because ok\n" * 28000,
            },
            2,
            {},
        ),
        ("no-marker", lambda: {"file_path": "a.py", "content": "x = 1\n" * 330000}, 0, {}),
    ],
    "sym": [
        ("continuation-lines", lambda: {"command": "echo App.dSYM \\\n" * 100000}, 2, {}),
        (
            "artifact-and-huge-token",
            lambda: {"command": "echo " + "x" * (2 * MB) + " App.dSYM"},
            2,
            {},
        ),
        ("rm-and-huge-token", lambda: {"command": "rm " + "x" * (2 * MB) + " App.dSYM"}, 2, {}),
        ("multibyte-no-artifact", lambda: {"command": "echo " + "é" * MB}, 0, {}),
        ("rm-no-artifact", lambda: {"command": "rm " + "x" * (2 * MB)}, 0, {}),
        ("escape-and-brace-runs", lambda: {"command": "echo $'\\x41'{a,b} " * 100000}, 0, {}),
        ("escape-and-near-dsym-runs", lambda: {"command": "echo $'\\x41'dsy " * 100000}, 0, {}),
    ],
    "erase": [
        ("continuation-lines", lambda: {"command": "st-flash read \\\n" * 100000}, 0, {}),
        ("openocd-words", lambda: {"command": "openocd é " * 200000}, 0, {}),
        ("st-flash-words", lambda: {"command": "st-flash é " * 200000}, 0, {}),
        ("commandfile-words", lambda: {"command": "-commandfile x " * 130000}, 0, {}),
        ("erase-words", lambda: {"command": "erase " * 340000}, 0, {}),
        ("erase-pipes", lambda: {"command": "erase | " * 290000}, 0, {}),
        ("jlink-words", lambda: {"command": "JLinkExe " * 220000}, 0, {}),
        ("jlink-words-with-carriage-returns", lambda: {"command": "JLinkExe\r\n" * 200000}, 0, {}),
        (
            "jlink-heredoc-words",
            lambda: {"command": "JLinkExe <<EOF\n" + "connect\n" * 250000},
            0,
            {},
        ),
        ("erase-at-the-end", lambda: {"command": "a " * MB + "&& st-flash erase"}, 2, {}),
        # redir() once rescanned the whole line for every descriptor copy, so the cost grew with
        # the square of the token count. The line reaches the J-Link scan (no probe pattern fires
        # first) and the erase is written to a file J-Link then reads, so the answer is 2.
        (
            "descriptor-copies-128k",
            lambda: {
                "command": "echo erase "
                + ">&1 " * 32000
                + "> c.jlink; JLinkExe -CommandFile c.jlink"
            },
            2,
            {},
        ),
        (
            "descriptor-copies-512k",
            lambda: {
                "command": "echo erase "
                + ">&1 " * 128000
                + "> c.jlink; JLinkExe -CommandFile c.jlink"
            },
            2,
            {},
        ),
        # Every heredoc, and every echo, writes `erase` to its own file and thousands of other
        # lines name J-Link, so comparing each file with each J-Link line is quadratic in the
        # input. The last row names the very last file, so the answer is found only at the end.
        (
            "heredoc-files-times-jlink-lines",
            lambda: {
                "command": "".join(f"cat <<E > f{i}\nerase\nE\n" for i in range(40000))
                + "jlink x\n" * 70000
            },
            0,
            {},
        ),
        (
            "writer-files-times-jlink-lines",
            lambda: {
                "command": "".join(f"echo erase > f{i}\n" for i in range(60000))
                + "jlink x\n" * 70000
            },
            0,
            {},
        ),
        (
            "writer-files-times-jlink-lines-named-at-the-end",
            lambda: {
                "command": "".join(f"echo erase > f{i}\n" for i in range(60000))
                + "jlink x\n" * 70000
                + "JLinkExe -CommandFile f59999"
            },
            2,
            {},
        ),
        # Under a UTF-8 locale GNU grep took quadratic time on the stdin patterns for this shape: a
        # word `erase` that is not alone before the `;`, and tens of thousands of J-Link commands.
        (
            "erase-argument-then-many-jlink-commands",
            lambda: {"command": "echo erase x; " + "JLinkExe -x f; " * 20000},
            0,
            {},
        ),
        # The digits before a descriptor copy are cut off the previous piece; an end-anchored
        # regex there retried at every digit, which took quadratic time in mawk.
        (
            "digit-run-before-descriptor-copy",
            lambda: {
                "command": "echo erase "
                + "9" * 200000
                + " >&1 > c.jlink; JLinkExe -CommandFile c.jlink"
            },
            2,
            {},
        ),
        # The three regexes that read a heredoc line were retried at every start position in mawk:
        # a J-Link word before a missing `<<`, `<<` before many pipes, and spaces after a pipe.
        (
            "jlink-words-after-heredoc-marker",
            lambda: {"command": "cat <<E " + "jlink " * 100000 + "\nx\nE"},
            0,
            {},
        ),
        (
            "pipes-after-heredoc-marker",
            lambda: {"command": "x <<E " + "|" * 200000 + "\nx\nE"},
            0,
            {},
        ),
        (
            "spaces-after-trailing-pipe",
            lambda: {"command": "cat <<E |" + " " * 500000 + "x\nx\nE"},
            0,
            {},
        ),
        (
            "many-jlink-lines-one-file",
            lambda: {"command": "echo erase > f\n" + "jlink x\n" * 200000},
            0,
            {},
        ),
        (
            "many-redirects-on-one-heredoc-line",
            lambda: {"command": "cat <<E" + " >f" * 300000 + "\nconnect\nE\njlink f"},
            0,
            {},
        ),
        (
            "jlink-erase-at-the-end",
            lambda: {"command": "a\n" * MB + "printf 'r\\nerase\\n' | JLinkExe"},
            2,
            {},
        ),
    ],
    "ddl": [
        ("continuation-lines", lambda: {"command": "echo \\\n" * 300000}, 0, {}),
        ("drop-words", lambda: {"command": "drop " * 400000}, 0, {}),
        ("multibyte-drop-words", lambda: {"command": "drop é " * 300000}, 0, {}),
        ("drop-at-the-end", lambda: {"command": "x " * MB + "DROP TABLE t"}, 2, {}),
        # Comment markers beside a drop are refused on sight; long runs of them must stay linear.
        ("open-comment-run-around-drop", lambda: {"command": "/*" * MB + " DROP TABLE t"}, 2, {}),
        ("close-comment-run-around-drop", lambda: {"command": "DROP TABLE t " + "*/" * MB}, 2, {}),
        (
            "executable-comment-run-around-drop",
            lambda: {"command": "DROP " + "/*!" * 300000 + " TABLE t"},
            2,
            {},
        ),
        (
            "mariadb-comment-run-around-drop",
            lambda: {"command": "DROP " + "/*M!" * 250000 + " TABLE t"},
            2,
            {},
        ),
        ("comment-markers-without-drop", lambda: {"command": "/*! */ " * 150000}, 0, {}),
        (
            "truncate-words-with-comment",
            lambda: {"command": "truncate -s 0 " * 70000 + "# c"},
            2,
            {},
        ),
    ],
    "retry": [
        (
            "no-match",
            lambda: {"file_path": "a.go", "content": " retr max_ret maxattempt xRetr " * 60000},
            0,
            {},
        ),
        ("multibyte", lambda: {"file_path": "a.go", "content": " retr é max_ret " * 120000}, 0, {}),
        (
            "retry-at-the-end",
            lambda: {"file_path": "a.go", "content": "x " * MB + "retry()"},
            2,
            {},
        ),
    ],
    "gen": [
        (
            "hex-run",
            lambda: {"file_path": "src/generated/v.c", "content": "0123456789abcdef" * 131072},
            0,
            {},
        ),
        (
            "near-sha-runs",
            lambda: {"file_path": "src/generated/v.c", "content": ("a" * 39 + "g") * 52000},
            0,
            {},
        ),
        (
            "near-dates",
            lambda: {"file_path": "src/generated/v.c", "content": "2024-01-0 " * 210000},
            0,
            {},
        ),
        (
            "multibyte",
            lambda: {"file_path": "src/generated/v.c", "content": "abcdef0123é " * 170000},
            0,
            {},
        ),
        (
            "stamp-at-the-end",
            lambda: {
                "file_path": "src/generated/v.c",
                "content": "x " * MB + "2024-01-02T03:04:05",
            },
            2,
            {},
        ),
    ],
    "mail": [
        (
            "near-unsubscribe",
            lambda: {"file_path": "emails/marketing/x.html", "content": "unsubscrib " * 190000},
            2,
            {},
        ),
        (
            "unsubscribe-at-the-end",
            lambda: {"file_path": "emails/marketing/x.html", "content": "x " * MB + "unsubscribe"},
            0,
            {},
        ),
    ],
    "game": [
        (
            "big-valid-array",
            lambda: {"file_path": "data/big-valid.json"},
            0,
            {"data/big-valid.json": "[" + "1," * MB + "1]"},
        ),
        (
            "big-many-values",
            lambda: {"file_path": "data/big-many.json"},
            2,
            {"data/big-many.json": "1 " * MB},
        ),
        (
            "big-bom-invalid-at-the-end",
            lambda: {"file_path": "data/big-bom.json"},
            2,
            {"data/big-bom.json": "\ufeff[" + "1," * MB + "]"},
        ),
    ],
    "ph": [
        (
            "near-marker",
            lambda: {"file_path": "applications/big-near.md"},
            0,
            {"applications/big-near.md": "[TK " * 500000},
        ),
        (
            "marker-at-the-end",
            lambda: {"file_path": "applications/big-end.md"},
            2,
            {"applications/big-end.md": "x " * MB + "[TK: a]\n"},
        ),
    ],
    # The hooks below read the written file from disk (like game and ph), so each row names the
    # file the test must write into the working directory first.
    "because": [
        (
            "many-rules-without-because",
            lambda: {"file_path": "interviews/decision-rule-big-bad.md"},
            2,
            {"interviews/decision-rule-big-bad.md": "If a, b\n" * 100000},
        ),
        (
            "many-wrapped-rules-without-because",
            lambda: {"file_path": "interviews/decision-rule-big-wrapped.md"},
            2,
            {"interviews/decision-rule-big-wrapped.md": "If a\ncont\n" * 90000},
        ),
        (
            "one-long-rule-line-with-because",
            lambda: {"file_path": "interviews/decision-rule-big-long-ok.md"},
            0,
            {"interviews/decision-rule-big-long-ok.md": "If x, y because " + "z" * 900000},
        ),
        (
            "one-long-rule-line-without-because",
            lambda: {"file_path": "interviews/decision-rule-big-long-bad.md"},
            2,
            {"interviews/decision-rule-big-long-bad.md": "If x, y " + "z" * 900000},
        ),
        (
            "long-space-run-before-rule",
            lambda: {"file_path": "interviews/decision-rule-big-spaces.md"},
            2,
            {"interviews/decision-rule-big-spaces.md": " " * 900000 + "If x"},
        ),
        (
            "no-rule-lines",
            lambda: {"file_path": "interviews/decision-rule-big-none.md"},
            0,
            {"interviews/decision-rule-big-none.md": "We looked at the lock.\n" * 40000},
        ),
        (
            "oversized-refusal",
            lambda: {"file_path": "interviews/decision-rule-big-over.md"},
            2,
            {"interviews/decision-rule-big-over.md": "x" * 1048577},
        ),
    ],
    "unit": [
        (
            "whitespace-line-then-absolute",
            lambda: {"file_path": "timing/ws.service"},
            0,
            {"timing/ws.service": "[Service]\n" + " " * 524288 + "~\nExecStart=/usr/bin/a\n"},
        ),
        (
            "prefix-run",
            lambda: {"file_path": "timing/prefix.service"},
            0,
            {"timing/prefix.service": "[Service]\nExecStart=" + "-@" * 262144 + "\n"},
        ),
        (
            "continuation-lines",
            lambda: {"file_path": "timing/cont.service"},
            0,
            {"timing/cont.service": "[Service]\n" + "ExecStart=\\\n" * 43000},
        ),
        (
            "huge-absolute-word",
            lambda: {"file_path": "timing/word.service"},
            0,
            {"timing/word.service": "[Service]\nExecStart=/" + "a" * 524288 + "\n"},
        ),
        (
            "huge-relative-word",
            lambda: {"file_path": "timing/rel.service"},
            2,
            {"timing/rel.service": "[Service]\nExecStart=." + "/" * 524288 + " x\n"},
        ),
        (
            "many-relative-lines",
            lambda: {"file_path": "timing/many.service"},
            2,
            {"timing/many.service": "[Service]\n" + "ExecStart=./x\n" * 40000},
        ),
        (
            "oversized-refusal",
            lambda: {"file_path": "timing/over.service"},
            2,
            {"timing/over.service": "[Service]\n" + "#" * 1_200_000 + "\n"},
        ),
    ],
    "safety": [
        (
            "many-bare-sites",
            lambda: {"file_path": "timing/many-bare.rs"},
            2,
            {"timing/many-bare.rs": "let a = unsafe { 1 };\n" * 40000},
        ),
        (
            "many-contracted-sites",
            lambda: {"file_path": "timing/many-ok.rs"},
            0,
            {"timing/many-ok.rs": "// SAFETY: ok\nlet a = unsafe { 1 };\n" * 26000},
        ),
        (
            "one-line-of-unsafe-words",
            lambda: {"file_path": "timing/words.rs"},
            0,
            {"timing/words.rs": "unsafe " * 140000},
        ),
        (
            "one-line-of-glued-unsafe",
            lambda: {"file_path": "timing/glued.rs"},
            0,
            {"timing/glued.rs": "unsafe" * 160000 + " {"},
        ),
        (
            "quote-pairs-then-site",
            lambda: {"file_path": "timing/quotes.rs"},
            2,
            {"timing/quotes.rs": '"a' * 300000 + " unsafe { }"},
        ),
        (
            "unterminated-quote-then-site",
            lambda: {"file_path": "timing/open-quote.rs"},
            2,
            {"timing/open-quote.rs": '"' + "x" * 900000 + " unsafe { }"},
        ),
        (
            "space-run-then-site",
            lambda: {"file_path": "timing/spaces.rs"},
            2,
            {"timing/spaces.rs": " " * 900000 + "unsafe {}"},
        ),
        (
            "site-on-the-last-line",
            lambda: {"file_path": "timing/last.rs"},
            2,
            {"timing/last.rs": "x = 1;\n" * 140000 + "unsafe { }\n"},
        ),
        (
            "many-lint-names",
            lambda: {"file_path": "timing/lints.rs"},
            0,
            {"timing/lints.rs": "#[allow(unsafe_code)]\nfn unsafe_op() {}\n" * 24000},
        ),
        (
            "oversized-refusal",
            lambda: {"file_path": "timing/over.rs"},
            2,
            {"timing/over.rs": "// SAFETY: ok\nlet a = unsafe { 1 };\n" * 32000},
        ),
    ],
    "closed": [
        (
            "many-closed-objects",
            lambda: {"file_path": "schemas/big-closed.json"},
            0,
            {"schemas/big-closed.json": CLOSED_BIG},
        ),
        (
            "many-open-objects-capped-report",
            lambda: {"file_path": "schemas/big-open.json"},
            2,
            {"schemas/big-open.json": OPEN_BIG},
        ),
        (
            "one-huge-property-name",
            lambda: {"file_path": "schemas/big-name.json"},
            2,
            {
                "schemas/big-name.json": '{"type":"object","properties":{"'
                + "k" * 900000
                + '":{"type":"object","properties":{}}},"additionalProperties":false}'
            },
        ),
        (
            "huge-allof-of-closed-objects",
            lambda: {"file_path": "schemas/big-allof.json"},
            0,
            {
                "schemas/big-allof.json": '{"allOf":['
                + ",".join(
                    ['{"type":"object","properties":{},"additionalProperties":false}'] * 15000
                )
                + "]}"
            },
        ),
        (
            "over-one-mebibyte-is-refused",
            lambda: {"file_path": "schemas/big-over.json"},
            2,
            {"schemas/big-over.json": '{"description":"' + "x" * 1100000 + '"}'},
        ),
    ],
    "otelmem": [
        (
            "many-pipelines-without-limiter",
            lambda: {"file_path": "otel-collector-big-pipes.yaml"},
            2,
            {
                "otel-collector-big-pipes.yaml": "service:\n  pipelines:\n"
                + "    p:\n      processors: [batch]\n" * 20000
            },
        ),
        (
            "long-flow-list-with-limiter-at-the-end",
            lambda: {"file_path": "otel-collector-big-flow.yaml"},
            0,
            {
                "otel-collector-big-flow.yaml": "pipelines:\n  t:\n    processors: ["
                + "a, " * 200000
                + "memory_limiter]\n"
            },
        ),
        (
            "many-comment-lines",
            lambda: {"file_path": "otel-collector-big-comments.yaml"},
            0,
            {
                "otel-collector-big-comments.yaml": (
                    "service:\n  pipelines:\n    t:\n      processors: [memory_limiter]\n"
                    + "      # c\n" * 80000
                )
            },
        ),
        (
            "oversized-refusal",
            lambda: {"file_path": "otel-collector-big-refused.yaml"},
            2,
            {"otel-collector-big-refused.yaml": "x" * (MB + 100000)},
        ),
    ],
    "conn": [
        (
            "many-evidenced-ceilings",
            lambda: {"file_path": "sysctl.d/big-ok.conf"},
            0,
            {"sysctl.d/big-ok.conf": "# peak 1\nnet.netfilter.nf_conntrack_max = 262144\n" * 14000},
        ),
        (
            "many-uncommented-ceilings",
            lambda: {"file_path": "sysctl.d/big-bad.conf"},
            2,
            {"sysctl.d/big-bad.conf": "net.netfilter.nf_conntrack_max = 1\n" * 25000},
        ),
        (
            "space-run-before-equals",
            lambda: {"file_path": "sysctl.d/big-spaces-eq.conf"},
            2,
            {"sysctl.d/big-spaces-eq.conf": "net.ipv4.tcp_tw_recycle" + " " * 900000 + "=1\n"},
        ),
        (
            "space-run-without-equals",
            lambda: {"file_path": "sysctl.d/big-spaces.conf"},
            0,
            {"sysctl.d/big-spaces.conf": "net.netfilter.nf_conntrack_max" + " " * 900000 + "x\n"},
        ),
        (
            "long-comment-line-then-key",
            lambda: {"file_path": "sysctl.d/big-comment.conf"},
            0,
            {"sysctl.d/big-comment.conf": "#" * 900000 + "9\nnet.nf_conntrack_max=1\n"},
        ),
        (
            "violation-at-the-end",
            lambda: {"file_path": "sysctl.d/big-end.conf"},
            2,
            {"sysctl.d/big-end.conf": "vm.x=1\n" * 100000 + "net.ipv4.tcp_tw_recycle=1\n"},
        ),
        (
            "oversized-refusal",
            lambda: {"file_path": "sysctl.d/big-over.conf"},
            2,
            {"sysctl.d/big-over.conf": "# 1\n" * 300000},
        ),
    ],
    "churn": [
        (
            "many-valid-rows",
            lambda: {"file_path": "churn/big-rows.csv"},
            0,
            {
                "churn/big-rows.csv": CHURN_HEADER
                + '1,Price,Champion left,"ticket 1: quote"\n' * 20000
            },
        ),
        (
            "one-long-evidence-cell",
            lambda: {"file_path": "churn/big-cell.csv"},
            0,
            {"churn/big-cell.csv": CHURN_HEADER + "1,Price,Champion left," + "x" * 900000 + "\n"},
        ),
        (
            "one-long-blank-evidence-cell",
            lambda: {"file_path": "churn/big-blank.csv"},
            2,
            {"churn/big-blank.csv": CHURN_HEADER + "1,Price,Champion left," + " " * 900000 + "\n"},
        ),
        (
            "blank-row-at-the-end",
            lambda: {"file_path": "churn/big-end.csv"},
            2,
            {
                "churn/big-end.csv": CHURN_HEADER
                + '1,Price,Champion left,"quote"\n' * 28000
                + "2,Price,Champion left,\n"
            },
        ),
        (
            "many-blank-rows",
            lambda: {"file_path": "churn/big-many-blank.csv"},
            2,
            {"churn/big-many-blank.csv": CHURN_HEADER + "1,Price,Champion left,\n" * 40000},
        ),
        (
            "one-line-of-commas",
            lambda: {"file_path": "churn/big-commas.csv"},
            0,
            {"churn/big-commas.csv": CHURN_HEADER + "," * 900000 + "\n"},
        ),
        (
            "doubled-quotes-in-one-cell",
            lambda: {"file_path": "churn/big-quotes.csv"},
            0,
            {
                "churn/big-quotes.csv": CHURN_HEADER
                + '1,Price,Champion left,"'
                + '""' * 450000
                + '"\n'
            },
        ),
        (
            "unclosed-quote-near-the-start",
            lambda: {"file_path": "churn/big-open.csv"},
            2,
            {"churn/big-open.csv": CHURN_HEADER + '1,Price,Champion left,"' + "x\n" * 400000},
        ),
        (
            "oversized-refusal",
            lambda: {"file_path": "churn/big-over.csv"},
            2,
            {"churn/big-over.csv": CHURN_HEADER + "x" * (1024 * 1024)},
        ),
    ],
    "mem": [
        # The sizes sit below 1 MiB except the refusal row, which is deliberately above.
        (
            "directive-after-long-prefix",
            lambda: {"file_path": "jobs/big-late.sbatch"},
            2,
            {"jobs/big-late.sbatch": "x " * 400000 + "\n#SBATCH --time=1\n"},
        ),
        (
            "many-directives-memory-last",
            lambda: {"file_path": "jobs/big-many.sbatch"},
            0,
            {"jobs/big-many.sbatch": "#SBATCH --time=1\n" * 30000 + "#SBATCH --mem=1G\n"},
        ),
        (
            "many-directives-no-memory",
            lambda: {"file_path": "jobs/big-nomem.sbatch"},
            2,
            {"jobs/big-nomem.sbatch": "#SBATCH --time=1\n" * 50000},
        ),
        (
            "near-miss-run",
            lambda: {"file_path": "jobs/big-near.sbatch"},
            2,
            {"jobs/big-near.sbatch": "#SBATCH " + "--mem-" * 90000 + "\n"},
        ),
        (
            "one-long-line-memory-at-the-end",
            lambda: {"file_path": "jobs/big-line.sbatch"},
            0,
            {"jobs/big-line.sbatch": "#SBATCH --time=1 " + "y" * 700000 + " --mem=1G\n"},
        ),
        (
            "oversize-refusal",
            lambda: {"file_path": "jobs/big-over.sbatch"},
            2,
            {"jobs/big-over.sbatch": "#SBATCH --mem=1G\n" + "y" * 1_100_000},
        ),
    ],
    "lock": [
        (
            "half-mib-dated-lines",
            lambda: {"file_path": "books/big-dated-close.md"},
            0,
            {"books/big-dated-close.md": "Period locked: yes, 2026-10-03\n" * 20000},
        ),
        (
            "many-undated-lines",
            lambda: {"file_path": "books/big-undated-close.md"},
            2,
            {"books/big-undated-close.md": "Period locked: yes\n" * 50000},
        ),
        (
            "one-long-lock-line",
            lambda: {"file_path": "books/big-line-close.md"},
            2,
            {"books/big-line-close.md": "Period locked: yes " * 50000 + "\n"},
        ),
        (
            "digit-run-after-lock",
            lambda: {"file_path": "books/big-digits-close.md"},
            2,
            {"books/big-digits-close.md": "Period locked: yes " + "1" * 900000 + "\n"},
        ),
        (
            "month-word-run",
            lambda: {"file_path": "books/big-months-close.md"},
            2,
            {"books/big-months-close.md": "Period locked: yes " + "jan" * 300000 + "\n"},
        ),
        (
            "no-lock-line",
            lambda: {"file_path": "books/big-none-close.md"},
            0,
            {"books/big-none-close.md": "x " * 500000},
        ),
        (
            "oversized-refusal",
            lambda: {"file_path": "books/big-over-close.md"},
            2,
            {"books/big-over-close.md": "x" * 1048577},
        ),
    ],
    "dmap": [
        (
            "many-entries-with-reasons",
            lambda: {"file_path": "timing/drift-map.yaml"},
            0,
            {"timing/drift-map.yaml": "ignore:\n" + "  - id: a\n    reason: r\n" * 30000},
        ),
        (
            "many-entries-no-reason",
            lambda: {"file_path": "timing/drift-map.yaml"},
            2,
            {"timing/drift-map.yaml": "ignore:\n" + "  - id: a\n" * 90000},
        ),
        (
            "one-long-id-line",
            lambda: {"file_path": "timing/drift-map.yaml"},
            0,
            {"timing/drift-map.yaml": "ignore:\n  - id: " + "x" * 900000 + "\n    reason: ok\n"},
        ),
        (
            "space-run-after-reason-key",
            lambda: {"file_path": "timing/drift-map.yaml"},
            2,
            {"timing/drift-map.yaml": "ignore:\n  - id: a\n    reason:" + " " * 900000 + "\n"},
        ),
        (
            "comment-run-after-entries",
            lambda: {"file_path": "timing/drift-map.yaml"},
            0,
            {"timing/drift-map.yaml": "ignore:\n  - id: a\n    reason: ok\n" + "# " * 400000},
        ),
        (
            "ignore-lookalike-words",
            lambda: {"file_path": "timing/drift-map.yaml"},
            0,
            {"timing/drift-map.yaml": "ignore " * 140000},
        ),
        (
            "deep-block-scalar",
            lambda: {"file_path": "timing/drift-map.yaml"},
            0,
            {
                "timing/drift-map.yaml": "ignore:\n  - id: a\n    reason: |\n"
                + "      text\n" * 80000
            },
        ),
    ],
    "sleep": [
        (
            "sleep-after-padding",
            lambda: {"file_path": "sl/tests/big-late.py"},
            2,
            {"sl/tests/big-late.py": "x = 1\n" * 80000 + "time.sleep(1)\n"},
        ),
        (
            "many-findings",
            lambda: {"file_path": "sl/tests/big-many.py"},
            2,
            {"sl/tests/big-many.py": "time.sleep(1)\n" * 40000},
        ),
        (
            "near-miss-run",
            lambda: {"file_path": "sl/tests/big-near.py"},
            0,
            {"sl/tests/big-near.py": "time.sleep" * 50000 + "\n"},
        ),
        (
            "one-long-line-sleep-at-the-end",
            lambda: {"file_path": "sl/tests/big-line.py"},
            2,
            {"sl/tests/big-line.py": "x" * 700000 + " time.sleep(1)\n"},
        ),
        (
            "one-long-line-clean",
            lambda: {"file_path": "sl/tests/big-clean.py"},
            0,
            {"sl/tests/big-clean.py": "x" * 700000 + " sleep\n"},
        ),
        (
            "oversize-refusal",
            lambda: {"file_path": "sl/tests/big-over.py"},
            2,
            {"sl/tests/big-over.py": "x = 1\n" + "y" * 1_100_000},
        ),
    ],
    "wfrun": [
        # Sizes sit below 1 MiB except the refusal row, which is deliberately above.
        (
            "sink-after-many-block-lines",
            lambda: {"file_path": ".github/workflows/big-late.yml"},
            2,
            {
                ".github/workflows/big-late.yml": "      - run: |\n"
                + "          echo padding ${{ github.sha }}\n" * 24000
                + "          echo ${{ github.head_ref }}\n"
            },
        ),
        (
            "many-safe-expressions-on-one-line",
            lambda: {"file_path": ".github/workflows/big-safe.yml"},
            0,
            {
                ".github/workflows/big-safe.yml": "      - run: echo "
                + "${{ github.sha }} " * 30000
                + "\n"
            },
        ),
        (
            "many-unsafe-expressions-on-one-line",
            lambda: {"file_path": ".github/workflows/big-unsafe.yml"},
            2,
            {
                ".github/workflows/big-unsafe.yml": "      - run: echo "
                + "${{ github.head_ref }} " * 24000
                + "\n"
            },
        ),
        (
            "long-run-of-list-dashes",
            lambda: {"file_path": ".github/workflows/big-dashes.yml"},
            0,
            {".github/workflows/big-dashes.yml": "- " * 300000 + "run: echo ${{ github.sha }}\n"},
        ),
        (
            "many-keys-before-the-block",
            lambda: {"file_path": ".github/workflows/big-keys.yml"},
            2,
            {
                ".github/workflows/big-keys.yml": "a: ${{ github.sha }}\n" * 30000
                + "      - run: |\n          echo ${{ github.event.issue.title }}\n"
            },
        ),
        (
            "wildcard-prefix-repeated-without-a-bracket",
            lambda: {"file_path": ".github/workflows/big-wild.yml"},
            0,
            {
                ".github/workflows/big-wild.yml": "      - run: echo ${{ github.sha "
                + WILD_PREFIX * 48000
                + "\n"
            },
        ),
        (
            "oversized-refusal",
            lambda: {"file_path": ".github/workflows/big-over.yml"},
            2,
            {".github/workflows/big-over.yml": "x" * (1024 * 1024 + 1)},
        ),
    ],
    "css": [
        (
            "width-after-long-clean-prefix",
            lambda: {"file_path": "css/big-late.css"},
            2,
            {"css/big-late.css": ".a{color:red}\n" * 45000 + ".b{width:100vw}\n"},
        ),
        (
            "many-near-misses-one-line",
            lambda: {"file_path": "css/big-near.css"},
            0,
            {"css/big-near.css": "border-width:100vw;" * 45000 + "\n"},
        ),
        (
            "full-bleed-last",
            lambda: {"file_path": "css/big-bleed.css"},
            0,
            {
                "css/big-bleed.css": ".b{width:100vw}\n" * 40000
                + ".c{margin-left:calc(50% - 50vw)}\n"
            },
        ),
    ],
    "slice": [
        (
            "waiver-at-end-of-large-file",
            lambda: {"file_path": "docs/slices/w-big/plan.md"},
            2,
            {"docs/slices/w-big/plan.md": "x " * 400000 + "\n## Waiver\n"},
        ),
        (
            "many-near-misses-then-waiver",
            lambda: {"file_path": "docs/slices/w-big/yield.md"},
            2,
            {"docs/slices/w-big/yield.md": "## Waived\n" * 60000 + "## Waiver\n"},
        ),
        (
            "large-file-no-waiver",
            lambda: {"file_path": "docs/slices/w-big/frame.md"},
            0,
            {"docs/slices/w-big/frame.md": "echo padding line here\n" * 40000},
        ),
        (
            "refused-over-1-mib",
            lambda: {"file_path": "docs/slices/w-big/inspect.md"},
            2,
            {"docs/slices/w-big/inspect.md": "a" * (1048576 + 1)},
        ),
    ],
    "adr": [
        (
            "heading-after-long-prefix",
            lambda: {"file_path": "docs/decisions/0100-big-late.md"},
            2,
            {"docs/decisions/0100-big-late.md": "x " * 400000 + "\n## Considered Options\n* a\n"},
        ),
        (
            "many-items",
            lambda: {"file_path": "docs/decisions/0101-big-many.md"},
            0,
            {"docs/decisions/0101-big-many.md": "## Considered Options\n" + "* x\n" * 150000},
        ),
        (
            "long-digit-run-is-not-an-item",
            lambda: {"file_path": "docs/decisions/0103-big-digits.md"},
            2,
            {"docs/decisions/0103-big-digits.md": "## Considered Options\n" + "9" * 500000 + "\n"},
        ),
        (
            "oversized-refusal",
            lambda: {"file_path": "docs/decisions/0104-big-over.md"},
            2,
            {"docs/decisions/0104-big-over.md": "x" * (1024 * 1024) + "\n## Considered Options\n"},
        ),
    ],
    "rbk": [
        (
            "stamp-after-long-first-line",
            lambda: {"file_path": "runbooks/big-a.md"},
            0,
            {"runbooks/big-a.md": "x " * 400000 + "\nOwner: sre\nLast verified: 2026-03-14\n"},
        ),
        (
            "no-stamp-long-line",
            lambda: {"file_path": "runbooks/big-b.md"},
            2,
            {"runbooks/big-b.md": "x " * 400000 + "\n"},
        ),
        (
            "no-stamp-many-lines",
            lambda: {"file_path": "runbooks/big-c.md"},
            2,
            {"runbooks/big-c.md": "x\n" * 300000},
        ),
        (
            "stamp-then-large-body",
            lambda: {"file_path": "runbooks/big-d.md"},
            0,
            {"runbooks/big-d.md": "Owner: sre\nLast verified: 2026-03-14\n" + "step\n" * 100000},
        ),
        (
            "oversized-refusal",
            lambda: {"file_path": "runbooks/big-e.md"},
            2,
            {"runbooks/big-e.md": "x" * (1024 * 1024 + 10)},
        ),
    ],
    "wkrev": [
        # Sizes sit below 1 MiB except the refusal row, which is deliberately above.
        (
            "commitments-after-long-prefix",
            lambda: {"file_path": "wk/reviews/big-prefix.md"},
            0,
            {
                "wk/reviews/big-prefix.md": "# Week of 5 Jan\n"
                + "padding line here\n" * 30000
                + "## Commitments\n1. a\n2. b\n3. c\n## Consciously not doing\n- x\n"
            },
        ),
        (
            "many-items-in-commitments",
            lambda: {"file_path": "wk/reviews/big-items.md"},
            2,
            {
                "wk/reviews/big-items.md": "# Week of 5 Jan\n## Commitments\n"
                + "- item\n" * 80000
                + "## Consciously not doing\n- x\n"
            },
        ),
        (
            "one-long-item-line",
            lambda: {"file_path": "wk/reviews/big-line.md"},
            0,
            {
                "wk/reviews/big-line.md": "# Week of 5 Jan\n## Commitments\n- "
                + "x" * 600000
                + "\n- b\n- c\n## Consciously not doing\n- x\n"
            },
        ),
        (
            "oversized-refusal",
            lambda: {"file_path": "wk/reviews/big-over.md"},
            2,
            {"wk/reviews/big-over.md": "# Week of 5 Jan\n" + "x" * (1024 * 1024)},
        ),
    ],
    "tlsoff": [
        (
            "minified-one-line-late-key",
            lambda: {"file_path": "cfg/big-min.json"},
            2,
            {"cfg/big-min.json": '{"a":' + '1,"b":' * 150000 + '"ssl_verify":false}'},
        ),
        (
            "many-findings",
            lambda: {"file_path": "cfg/big-many.yaml"},
            2,
            {"cfg/big-many.yaml": "ssl_verify: false\n" * 55000},
        ),
        (
            "many-near-misses",
            lambda: {"file_path": "cfg/big-near.yaml"},
            0,
            {"cfg/big-near.yaml": "ssl_verify: truex " * 55000 + "\n"},
        ),
        (
            "over-limit-refused",
            lambda: {"file_path": "cfg/big-over.json"},
            2,
            {"cfg/big-over.json": "x" * (1024 * 1024 + 1)},
        ),
    ],
}

# A match on the first line of a multi-line input, followed by more than a pipe buffer of further
# lines. `grep -q` quits at the match and a writer piped into it dies of SIGPIPE, which `pipefail`
# turns into a failed pipeline; a hook that read that as "no match" allowed the command.
LINES = "echo padding line here\n" * 40000
EARLY = {
    "tf": [
        (
            "violation-first-line",
            lambda: {"command": "terraform apply -auto-approve\n" + LINES},
            2,
            {},
        )
    ],
    "kill": [
        (
            "violation-first-line",
            lambda: {"command": "select pg_terminate_backend(pid)\n" + LINES},
            2,
            {},
        )
    ],
    "sup": [
        (
            "violation-first-line",
            lambda: {"file_path": "a.py", "content": "x = 1  # pragma: no mutate\n" + LINES},
            2,
            {},
        )
    ],
    "sym": [("violation-first-line", lambda: {"command": "rm App.dSYM\n" + LINES}, 2, {})],
    "erase": [("violation-first-line", lambda: {"command": "st-flash erase\n" + LINES}, 2, {})],
    "ddl": [("violation-first-line", lambda: {"command": "DROP TABLE t\n" + LINES}, 2, {})],
    "retry": [
        (
            "violation-first-line",
            lambda: {"file_path": "a.go", "content": "retry()\n" + LINES},
            2,
            {},
        ),
    ],
    "gen": [
        (
            "violation-first-line",
            lambda: {"file_path": "src/generated/v.c", "content": "2024-01-02T03:04:05\n" + LINES},
            2,
            {},
        )
    ],
    "mail": [
        (
            "unsubscribe-first-line",
            lambda: {"file_path": "emails/marketing/x.html", "content": "unsubscribe\n" + LINES},
            0,
            {},
        )
    ],
    "game": [
        (
            "invalid-after-a-long-first-line",
            lambda: {"file_path": "data/early.json"},
            2,
            {"data/early.json": "{" + LINES},
        )
    ],
    "ph": [
        (
            "tk-first-line",
            lambda: {"file_path": "applications/big-first.md"},
            2,
            {"applications/big-first.md": "[TK: a]\n" + LINES},
        )
    ],
    "otelmem": [
        (
            "pipelines-first-line",
            lambda: {"file_path": "otel-collector-big-first.yaml"},
            2,
            {
                "otel-collector-big-first.yaml": "pipelines:\n  t:\n    processors: [batch]\n"
                + LINES
            },
        )
    ],
    "conn": [
        (
            "violation-first-line",
            lambda: {"file_path": "sysctl.d/early.conf"},
            2,
            {"sysctl.d/early.conf": "net.ipv4.tcp_tw_recycle=1\n" + LINES},
        )
    ],
    "churn": [
        (
            "blank-first-row",
            lambda: {"file_path": "churn/early.csv"},
            2,
            {
                "churn/early.csv": CHURN_HEADER
                + "1,Price,Champion left,\n"
                + '2,Price,Champion left,"q"\n' * 20000
            },
        )
    ],
    "mem": [
        (
            "memory-first-line",
            lambda: {"file_path": "jobs/big-first.sbatch"},
            0,
            {"jobs/big-first.sbatch": "#SBATCH --mem=1G\n" + LINES},
        )
    ],
    "adr": [
        (
            "padding-then-one-option",
            lambda: {"file_path": "docs/decisions/0102-big-pad.md"},
            2,
            {"docs/decisions/0102-big-pad.md": LINES + "## Considered Options\n* a\n"},
        ),
    ],
}
for _key, _items in EARLY.items():
    BIG[_key] = BIG[_key] + _items

BIG_CASES = [
    pytest.param(key, name, build, want, files, id=f"{key}-{name}")
    for key, items in BIG.items()
    for name, build, want, files in items
]


SUP_LIMIT = 1024 * 1024


def test_the_sup_timing_rows_reach_the_awk_pass():
    """A timing row that hits the size refusal measures nothing about the scan. Every row that
    holds a marker is below the limit, except the refusal row; the row without a marker never
    reaches the refusal, whatever its size."""
    for name, build, _, _ in BIG["sup"]:
        if name == "no-marker":
            continue
        size = len(build()["content"].encode("utf-8"))
        assert (size > SUP_LIMIT) == (name == "oversized-refusal"), (name, size)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("name", ["many-bare-markers", "one-long-marker-line"])
def test_a_large_bare_marker_is_judged_not_refused(name, mode, bins, scratch):
    build = {n: b for n, b, _, _ in BIG["sup"]}[name]
    stdin = json.dumps({"tool_input": build()}, ensure_ascii=False).encode("utf-8")
    done = run_hook("sup", stdin, mode, bins, scratch, timeout=5)
    assert done.returncode == 2
    assert b"needs a reason" in done.stderr
    assert b"larger than" not in done.stderr


# A payload per hook that is innocent (or, for tf and sym, at least not decided before the first
# grep) and larger than the 64 KiB bash keeps in a pipe for a here-string, so the here-string goes
# through a temporary file. With the file-size limit at 1 KiB that write fails, the redirection
# fails with status 1, and grep never runs. A hook that read that status as "no match" would allow
# the command; each must refuse with exit 2 instead. The hooks that read a file and have no
# here-string (see FILE_ONLY) have no such write to fail.
HUGE = 100_000
NO_SCAN = {
    "tf": lambda: {"command": "terraform plan " + "x" * HUGE},
    "kill": lambda: {"command": "echo " + "x" * HUGE},
    "sup": lambda: {"file_path": "a.py", "content": "# pragma: no mutate ok\n" + "x = 1\n" * 20000},
    "sym": lambda: {"command": "echo " + "x" * HUGE},
    "erase": lambda: {"command": "echo " + "x" * HUGE},
    "ddl": lambda: {"command": "echo " + "x" * HUGE},
    "retry": lambda: {"file_path": "a.go", "content": "x = 1\n" * 20000},
    "gen": lambda: {"file_path": "src/generated/v.c", "content": "x = 1\n" * 20000},
    "mail": lambda: {"file_path": "emails/marketing/x.html", "content": "x = 1\n" * 20000},
    # The closed-object hook reads the file but pipes its findings through a here-string; this
    # schema has enough open objects that the findings outgrow the 1 KiB write limit.
    "closed": lambda: {"file_path": "schemas/many-open.json"},
}


FILE_ONLY = {
    "ph",
    "game",
    "because",
    "unit",
    "safety",
    "otelmem",
    "conn",
    "churn",
    "mem",
    "lock",
    "dmap",
    "sleep",
    "wfrun",
    "css",
    "slice",
    "adr",
    "rbk",
    "wkrev",
    "tlsoff",
}


def test_no_scan_case_for_every_hook_with_a_here_string():
    assert set(NO_SCAN) == set(HOOK_FILES) - FILE_ONLY


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("key", sorted(NO_SCAN))
def test_a_here_string_that_cannot_be_written_refuses(key, mode, bins, scratch):
    if mode not in bins:
        pytest.skip(f"the {mode} parser mode needs {' and '.join(MODES[mode])} on PATH")
    stdin = json.dumps({"tool_input": NO_SCAN[key]()}, ensure_ascii=False).encode("utf-8")
    env = {"PATH": str(bins[mode][key]), "LANG": "C.UTF-8", "HOME": str(scratch)}
    # ulimit -f is in 1 KiB units; ignoring SIGXFSZ turns the over-limit write into an error
    # instead of killing bash, which is what a full disk gives.
    script = 'ulimit -f 1; trap "" XFSZ; exec "$0" "$1"'
    done = subprocess.run(  # noqa: S603
        [_path_for("bash"), "-c", script, _path_for("bash"), str(_hook_path(key))],
        input=stdin,
        capture_output=True,
        cwd=scratch,
        env=env,
        timeout=30,
        check=False,
    )
    assert done.returncode == 2, done.stderr.decode("utf-8", "replace")[-300:]
    assert b"blocked: could not scan" in done.stderr


def test_every_hook_has_a_timing_case():
    assert set(BIG) == set(HOOK_FILES)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(("key", "name", "build", "want", "files"), BIG_CASES)
def test_a_large_payload_stays_within_its_cpu_budget(
    key, name, build, want, files, mode, bins, scratch
):
    for rel, text in files.items():
        target = scratch / rel
        # A kit hook's timing file may sit in a directory no scratch file created.
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    tool_input = build()
    stdin = json.dumps({"tool_input": tool_input}, ensure_ascii=False).encode("utf-8")
    done, spent = run_hook_timed(key, stdin, mode, bins, scratch)
    assert done.returncode == want, (spent, done.stderr.decode("utf-8", "replace")[:300])
    budget = cpu_budget(key, tool_input, mode, bins, scratch)
    assert spent < budget, f"{HOOK_FILES[key]} ({mode}) spent {spent:.1f} of {budget:.1f} CPU s"


# One long run of a single kind of character, then a character nothing matches, in front of a
# word the hook looks for, after it, or alone. A regex that is retried at every start position, or
# that backtracks over two adjacent repeats, takes time that grows with the square of the run, and
# a timed-out hook fails open. This covers the normalising hooks, which read a whole command.
RUN_LENGTH = 512 * 1024
RUN_UNITS = {
    "digits": "9",
    "spaces": " ",
    "backslashes": "\\",
    "letters": "a",
    "hashes": "#",
    "comment-opens": "/*",
    "double-slashes": "//",
    "dashes": "--",
}
RUN_WORDS = {
    "tf": "terraform apply",
    "kill": "pg_terminate_backend(",
    "sym": "rm mapping.txt",
    "erase": "echo erase",
    "ddl": "truncate",
}
RUN_SHAPES = {
    "alone": lambda run, word: run + "~",
    "before-word": lambda run, word: run + "~ " + word,
    "after-word": lambda run, word: word + " " + run + "~",
}


def test_every_normalising_hook_has_a_word_for_the_run_tests():
    assert set(RUN_WORDS) == set(NORMALISING)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("shape", RUN_SHAPES)
@pytest.mark.parametrize("unit", RUN_UNITS)
@pytest.mark.parametrize("key", NORMALISING)
def test_a_long_run_of_one_character_stays_within_its_cpu_budget(
    key, unit, shape, mode, bins, scratch
):
    command = RUN_SHAPES[shape]((RUN_UNITS[unit] * RUN_LENGTH)[:RUN_LENGTH], RUN_WORDS[key])
    stdin = json.dumps({"tool_input": {"command": command}}).encode("utf-8")
    done, spent = run_hook_timed(key, stdin, mode, bins, scratch)
    assert done.returncode in (0, 2), (spent, done.stderr.decode("utf-8", "replace")[:300])
    budget = cpu_budget(key, {"command": command}, mode, bins, scratch)
    assert spent < budget, f"{HOOK_FILES[key]} ({mode}) spent {spent:.1f} of {budget:.1f} CPU s"
