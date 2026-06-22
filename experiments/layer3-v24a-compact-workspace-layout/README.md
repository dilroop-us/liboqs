# Layer 3 v24a: Compact ML-DSA Lifecycle Workspace Layout Analysis

## Goal

Analyze whether the separate v21/v22b/v23b ML-DSA workspaces can be represented as one compact lifecycle workspace.

v24a is analysis only. It does not modify ML-DSA implementation code.

## Background

After v23b, the current explicit workspace accounting is:

- Unified sign workspace: 44064 B
- Verify workspace: 8128 B
- Keygen workspace: 10240 B
- Separate total: 62432 B

The high-level ML-DSA stack is already low after previous versions:

- v21: low-stack signing workspace
- v22b: low-stack verification workspace
- v23b: low-stack keygen/provisioning workspace

## v24a model

v24a models a compact lifecycle workspace with:

1. One common matrix region
2. One union of operation-specific regions

The operation-specific regions are:

- sign operation buffers
- verify operation buffers
- keygen/provisioning operation buffers

## Compact workspace estimate

Current separate workspace total:

- 62432 B

Compact lifecycle workspace estimate:

- 44064 B

Savings:

- 18368 B
- about 29.4%

## Safety conditions

The compact layout is safe if:

- one workspace is used by one thread/context at a time
- sign, verify, and keygen operations are not concurrent on the same workspace
- the matrix region is shared but kept separate from operation-specific buffers
- operation-specific buffers share a union
- keygen buffers are cleaned before pairwise consistency testing enters sign/verify paths

## Outputs

Generated outputs:

- layer3-results/v24a_current_workspace_symbols.csv
- layer3-results/v24a_workspace_size_compare.csv
- layer3-results/v24a_workspace_layout_report.md
- layer3-results/v24a_call_order_checks.md
- layer3-results/v24a_compact_workspace_final_report.md

## Conclusion

v24a predicts that the separate v21/v22b/v23b ML-DSA workspaces can be compacted from 62432 B to about 44064 B, saving 18368 B, without increasing stack usage.

## Next step

v24b should implement one compact lifecycle workspace API.
