#!/usr/bin/env python3

import base64
import json
import sys
import os
import argparse

def encode_config(host, key, api=None, relay=None):
    """Encode config data into a Base64-URL-safe string"""
    # Create the config object
    config = {
        'host': host,
        'key': key,
        'api': api or '',
        'relay': relay or ''
    }
    
    # Serialize to JSON
    json_data = json.dumps(config, separators=(',', ':'))
    
    # Reverse the string
    reversed_data = json_data[::-1]
    
    # Encode with URL-safe Base64 (without padding)
    encoded = base64.urlsafe_b64encode(reversed_data.encode('utf-8')).decode('utf-8')
    
    # Remove padding
    encoded = encoded.rstrip('=')
    
    # Create the filename-safe string
    filename_safe = f"host={host},key={key}"
    if api:
        filename_safe += f",api={api}"
    if relay:
        filename_safe += f",relay={relay}"
    
    # Create the config block
    config_block = f"""custom-rendezvous-server = "{encoded}"
key = "{key}" """
    
    return encoded, filename_safe, config_block

def decode_config(encoded_string):
    """Decode a Base64-URL-safe string back to JSON"""
    # Add padding if needed
    padding = 4 - (len(encoded_string) % 4)
    if padding != 4:
        encoded_string += '=' * padding
    
    try:
        # Decode Base64
        decoded_bytes = base64.urlsafe_b64decode(encoded_string)
        decoded_string = decoded_bytes.decode('utf-8')
        
        # Reverse the string
        reversed_string = decoded_string[::-1]
        
        # Parse JSON
        json_data = json.loads(reversed_string)
        return json_data
    except Exception as e:
        raise ValueError(f"Failed to decode: {str(e)}")

def backup_config():
    """Read local host config from RustDesk config file"""
    config_path = os.path.expanduser("~/Library/Application Support/RustDesk/config/RustDesk2.toml")
    
    if not os.path.exists(config_path):
        raise FileNotFoundError("RustDesk config file not found")
    
    # Read the config file
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Extract host and key (simplified parsing)
    host = ""
    key = ""
    
    for line in content.split('\n'):
        if line.startswith('custom-rendezvous-server'):
            # Extract the encoded string from the value
            encoded = line.split('=')[1].strip().strip('"')
            try:
                config_data = decode_config(encoded)
                host = config_data.get('host', '')
                key = config_data.get('key', '')
                break
            except Exception:
                pass
                
    return host, key

def main():
    parser = argparse.ArgumentParser(description='RustDesk config string encoder/decoder')
    subparsers = parser.add_subparsers(dest='command', help='Subcommands')
    
    # Encode subcommand
    encode_parser = subparsers.add_parser('encode', help='Encode config')
    encode_parser.add_argument('--host', required=True, help='Host')
    encode_parser.add_argument('--key', required=True, help='Key')
    encode_parser.add_argument('--api', help='API')
    encode_parser.add_argument('--relay', help='Relay')
    
    # Decode subcommand
    decode_parser = subparsers.add_parser('decode', help='Decode config')
    decode_parser.add_argument('string_or_filename', help='Encoded string or filename')
    
    # Backup subcommand
    backup_parser = subparsers.add_parser('backup', help='Backup config from local file')
    
    args = parser.parse_args()
    
    try:
        if args.command == 'encode':
            encoded, filename_safe, config_block = encode_config(args.host, args.key, args.api, args.relay)
            print(f"Encoded string: {encoded}")
            print(f"Filename-safe: {filename_safe}")
            print(f"Config block:\n{config_block}")
            
        elif args.command == 'decode':
            # Check if it's a file or string
            if os.path.exists(args.string_or_filename):
                with open(args.string_or_filename, 'r') as f:
                    encoded_string = f.read().strip()
            else:
                encoded_string = args.string_or_filename
                
            decoded = decode_config(encoded_string)
            print(json.dumps(decoded, indent=2))
            
        elif args.command == 'backup':
            host, key = backup_config()
            if host and key:
                encoded, filename_safe, config_block = encode_config(host, key)
                print(f"Encoded string: {encoded}")
                print(f"Filename-safe: {filename_safe}")
                print(f"Config block:\n{config_block}")
            else:
                print("No valid host/key found in config")
                sys.exit(1)
                
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()