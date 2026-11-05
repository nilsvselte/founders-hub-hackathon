---
name: hackathon-demo
description: The live hackathon demo. Use when preparing, rehearsing, or running the demo, or when deciding what a feature must show on stage.
---

# Hackathon demo

## The story

Use one physical button, two sample rooms, and one standby request:

1. Show that the buyer has no matching slot.
2. Press **Release room** on the Atech device.
3. Show the agent find a match and quote it.
4. Accept the offer and show a confirmed test booking.

## Run it

- The 90-second script, with exact screens, prices, and ports, is [marketplace/DEMO.md](../../../marketplace/DEMO.md).
- Start the stack with `MARKETPLACE_DEMO_MODE=1`; see "Try the booking demo" in [marketplace/README.md](../../../marketplace/README.md).
- Without `ANTHROPIC_API_KEY`, demo mode uses a deterministic matcher and labels offers **Demo match**.
- For the physical button, the board and the device server must be on the same 2.4 GHz network; see [device/README.md](../../../device/README.md).
