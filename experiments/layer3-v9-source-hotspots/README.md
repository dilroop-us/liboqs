# Layer 3 v9: Source Hotspot Mapping

## Goal

v9 maps the memory hotspots found in v8 to actual liboqs ML-DSA-44 source functions and files.

## Why this matters

v8 showed that ML-DSA-44 sign and verify are the highest memory-pressure operations:

| Operation | Peak heap | Peak stack | Peak total |
|---|---:|---:|---:|
| ML-DSA-44 sign | 8236 B | 50904 B | 59224 B |
| ML-DSA-44 verify | 8236 B | 50904 B | 59224 B |

Before changing implementation internals, v9 identifies which source areas are responsible.

## Focused implementation path

Current platform/build uses the native ML-DSA-44 x86_64 implementation:

```text
src/sig/ml_dsa/mldsa-native_ml-dsa-44_x86_64/mldsa/src/
