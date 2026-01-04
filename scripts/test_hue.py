#!/usr/bin/env python3
"""
Quick test script to verify Hue connection works.
"""

from dotenv import load_dotenv
import os
from src.hue_controller import HueController

load_dotenv()

print("Testing Hue Connection...")
print("=" * 60)

hue = HueController(
    bridge_ip=os.getenv('HUE_BRIDGE_IP'),
    username=os.getenv('HUE_USERNAME')
)

print(f"Bridge IP: {os.getenv('HUE_BRIDGE_IP')}")
print(f"Username: {os.getenv('HUE_USERNAME')[:10]}...")

if hue.test_connection():
    print("\n✓ Connection successful!")

    lights = hue.get_lights()
    print(f"\nFound {len(lights)} lights:")
    for light_id, light in lights.items():
        name = light.get('name')
        state = light.get('state', {})
        on = "ON" if state.get('on') else "OFF"
        reachable = "✓" if state.get('reachable') else "✗"
        print(f"  [{light_id}] {name} - {on} {reachable}")
else:
    print("\n✗ Connection failed")
