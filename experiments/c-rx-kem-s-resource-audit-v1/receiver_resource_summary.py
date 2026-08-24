#!/usr/bin/env python3

workspace = 13088
indcpa_dec_workspace = 4864

secret_key = 2400
ciphertext = 1088
shared_secret = 32

top_frame = 1376

current_component_lower_bound = (
    workspace
    + secret_key
    + ciphertext
    + shared_secret
    + top_frame
)

s1_candidate_workspace = 9984

s1_component_lower_bound = (
    s1_candidate_workspace
    + secret_key
    + ciphertext
    + shared_secret
    + top_frame
)

print("C-RX-KEM-S receiver resource summary")
print()

print("Measured / established")
print("----------------------")
print(f"Full receiver workspace peak:  {workspace:6d} B")
print(f"IND-CPA decrypt workspace:      {indcpa_dec_workspace:6d} B")
print(f"Persistent secret key:          {secret_key:6d} B")
print(f"Ciphertext input:               {ciphertext:6d} B")
print(f"Shared-secret output:           {shared_secret:6d} B")
print(f"Known top-level stack frame:    {top_frame:6d} B")

print()
print(
    f"Current component lower bound:  "
    f"{current_component_lower_bound:6d} B"
)

print()
print("Analytical S1 hypothesis")
print("------------------------")
print(
    f"Delayed-schedule workspace:     "
    f"{s1_candidate_workspace:6d} B"
)

print(
    f"S1 component lower bound:       "
    f"{s1_component_lower_bound:6d} B"
)

print(
    f"potential component saving:      "
    f"{current_component_lower_bound - s1_component_lower_bound:6d} B"
)

print()
print(
    "WARNING: these are component models, not measured total RAM. "
    "Nested call-stack peak, protocol state, OS/runtime memory, "
    "and application buffers remain outside the model."
)
