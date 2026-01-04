#!/usr/bin/env python3
"""
Philips Hue Bridge Authentication Script
Discovers the bridge, authenticates, and saves API credentials.
"""

import requests
import json
import time
from pathlib import Path

BRIDGE_IP = "192.168.0.245"
CONFIG_FILE = Path(__file__).parent / ".hue_config"


def discover_bridge():
    """Discover Hue bridge on the network."""
    print("Discovering Philips Hue bridge...")
    try:
        response = requests.get("https://discovery.meethue.com/", timeout=5)
        bridges = response.json()
        if bridges:
            bridge = bridges[0]
            print(f"✓ Found bridge: {bridge['internalipaddress']}")
            print(f"  Bridge ID: {bridge['id']}")
            return bridge['internalipaddress']
        else:
            print("✗ No bridges found")
            return None
    except Exception as e:
        print(f"✗ Error discovering bridge: {e}")
        return None


def get_bridge_info(bridge_ip):
    """Get bridge configuration and info."""
    try:
        response = requests.get(f"https://{bridge_ip}/api/config", verify=False, timeout=5)
        config = response.json()
        print(f"\nBridge Info:")
        print(f"  Name: {config.get('name')}")
        print(f"  API Version: {config.get('apiversion')}")
        print(f"  Software Version: {config.get('swversion')}")
        return config
    except Exception as e:
        print(f"✗ Error getting bridge info: {e}")
        return None


def create_user(bridge_ip, app_name="spottyhue#dev"):
    """Create an authenticated user on the Hue bridge."""
    print(f"\n{'='*60}")
    print("AUTHENTICATION REQUIRED")
    print(f"{'='*60}")
    print("\nPlease press the LINK BUTTON on your Hue Bridge now.")
    print("You have 30 seconds...\n")

    for i in range(30, 0, -1):
        print(f"Waiting... {i}s ", end='\r')
        time.sleep(1)

        if i % 2 == 0:  # Try every 2 seconds
            try:
                payload = {"devicetype": app_name}
                response = requests.post(
                    f"https://{bridge_ip}/api",
                    json=payload,
                    verify=False,
                    timeout=5
                )
                result = response.json()[0]

                if "success" in result:
                    username = result["success"]["username"]
                    print(f"\n\n✓ Authentication successful!           ")
                    print(f"  Username: {username}")
                    return username
                elif "error" in result:
                    error_type = result["error"].get("type")
                    if error_type != 101:  # 101 is "link button not pressed"
                        print(f"\n✗ Error: {result['error'].get('description')}")
                        return None
            except Exception as e:
                continue

    print("\n\n✗ Timeout - Bridge button was not pressed in time")
    return None


def save_config(bridge_ip, username):
    """Save bridge configuration to file."""
    config = {
        "bridge_ip": bridge_ip,
        "username": username
    }

    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"\n✓ Configuration saved to: {CONFIG_FILE}")

    # Also create a .env file for convenience
    env_file = Path(__file__).parent / ".env"
    with open(env_file, 'w') as f:
        f.write(f"HUE_BRIDGE_IP={bridge_ip}\n")
        f.write(f"HUE_USERNAME={username}\n")

    print(f"✓ Environment file saved to: {env_file}")


def load_config():
    """Load existing configuration."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return None


def test_connection(bridge_ip, username):
    """Test the API connection by getting lights."""
    print("\nTesting connection...")
    try:
        response = requests.get(
            f"https://{bridge_ip}/api/{username}/lights",
            verify=False,
            timeout=5
        )
        lights = response.json()

        if isinstance(lights, dict) and not any("error" in str(v) for v in lights.values()):
            print(f"✓ Successfully connected! Found {len(lights)} light(s):")
            for light_id, light_data in lights.items():
                name = light_data.get('name', 'Unknown')
                state = "ON" if light_data.get('state', {}).get('on') else "OFF"
                print(f"  [{light_id}] {name} - {state}")
            return True
        else:
            print(f"✗ Connection test failed: {lights}")
            return False
    except Exception as e:
        print(f"✗ Error testing connection: {e}")
        return False


def main():
    """Main authentication flow."""
    print("Philips Hue Bridge Authentication")
    print("=" * 60)

    # Check for existing config
    existing_config = load_config()
    if existing_config:
        print(f"\n✓ Found existing configuration:")
        print(f"  Bridge IP: {existing_config['bridge_ip']}")
        print(f"  Username: {existing_config['username']}")

        choice = input("\nUse existing config? (y/n): ").lower()
        if choice == 'y':
            if test_connection(existing_config['bridge_ip'], existing_config['username']):
                print("\n✓ All set! You can now use the Hue API.")
                return
            else:
                print("\n✗ Existing config is invalid. Creating new credentials...")

    # Discover bridge
    bridge_ip = discover_bridge()
    if not bridge_ip:
        bridge_ip = BRIDGE_IP
        print(f"Using default bridge IP: {bridge_ip}")

    # Get bridge info
    get_bridge_info(bridge_ip)

    # Authenticate
    username = create_user(bridge_ip)
    if not username:
        print("\n✗ Authentication failed. Please try again.")
        return

    # Save configuration
    save_config(bridge_ip, username)

    # Test connection
    test_connection(bridge_ip, username)

    print("\n" + "=" * 60)
    print("✓ Setup complete! Your API credentials are ready to use.")
    print("=" * 60)


if __name__ == "__main__":
    # Disable SSL warnings since Hue bridge uses self-signed cert
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    main()
