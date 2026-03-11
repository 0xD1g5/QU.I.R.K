#!/usr/bin/env python3
"""
Phase 5 — Long-Term Memory Poisoning (Full chain: plant + detonate)
ATLAS: AML-T0040
Target: QL-FraudSentinel

Plants adversarial embedding if not already present, then triggers scoring to detonate.
"""

import os
import sys

# Plant poison (if not already done by Phase 3/4)
from plant_poison import plant
from trigger import trigger


def main():
    print("\n[*] Phase 5 — Long-Term Memory Poisoning")
    print("[*] Step 1: Ensure poison is planted...\n")
    planted = plant(verbose=True)

    print("\n[*] Step 2: Trigger detonation — analyst submits transaction...\n")
    trigger()


if __name__ == "__main__":
    main()
