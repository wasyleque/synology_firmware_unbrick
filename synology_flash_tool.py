#!/usr/bin/env python3
"""
Synology Flash Tool - Automatic firmware image creator for SPI flash
Supports: DS213+, and other PPC/MVortex platforms

Usage:
    python synology_flash_tool.py --model DS213+ --mac 00113218139B --sn CAL1N10509
    python synology_flash_tool.py --interactive
    python synology_flash_tool.py --list-models
"""

import os
import sys
import struct
import argparse
import hashlib
from pathlib import Path

# Platform configurations
PLATFORMS = {
    'DS213+': {
        'name': 'DS213+',
        'hw_version': 'DS213pv10',
        'flash_size': 8 * 1024 * 1024,  # 8MB
        'uboot_offset': 0x000000,
        'uboot_max_size': 0x090000,
        'zimage_offset': 0x090000,
        'zimage_max_size': 0x300000,
        'rdbin_offset': 0x390000,
        'rdbin_max_size': 0x440000,
        'vendor_offset': 0x7D0000,
        'vendor_size': 0x10000,
        'dts_offset': 0x7E0000,
        'dts_size': 0x10000,
        'fis_offset': 0x7F0000,
        'bootargs': 'root=/dev/md0 rw syno_hw_version=DS213pv10 console=ttyS0,115200 ip=off ihd_num=2 netif_num=1 ip=off initrd=0x2000040,4M',
    },
    'DS213': {
        'name': 'DS213',
        'hw_version': 'DS213pv10',
        'flash_size': 8 * 1024 * 1024,
        'uboot_offset': 0x000000,
        'uboot_max_size': 0x090000,
        'zimage_offset': 0x090000,
        'zimage_max_size': 0x300000,
        'rdbin_offset': 0x390000,
        'rdbin_max_size': 0x440000,
        'vendor_offset': 0x7D0000,
        'vendor_size': 0x10000,
        'dts_offset': 0x7E0000,
        'dts_size': 0x10000,
        'fis_offset': 0x7F0000,
        'bootargs': 'root=/dev/md0 rw syno_hw_version=DS213pv10 console=ttyS0,115200 ip=off ihd_num=2 netif_num=1 ip=off initrd=0x2000040,4M',
    },
    'DS212+': {
        'name': 'DS212+',
        'hw_version': 'DS212pv10',
        'flash_size': 8 * 1024 * 1024,
        'uboot_offset': 0x000000,
        'uboot_max_size': 0x090000,
        'zimage_offset': 0x090000,
        'zimage_max_size': 0x300000,
        'rdbin_offset': 0x390000,
        'rdbin_max_size': 0x440000,
        'vendor_offset': 0x7D0000,
        'vendor_size': 0x10000,
        'dts_offset': 0x7E0000,
        'dts_size': 0x10000,
        'fis_offset': 0x7F0000,
        'bootargs': 'root=/dev/md0 rw syno_hw_version=DS212pv10 console=ttyS0,115200 ip=off ihd_num=2 netif_num=1 ip=off initrd=0x2000040,4M',
    },
    'DS212': {
        'name': 'DS212',
        'hw_version': 'DS212pv10',
        'flash_size': 8 * 1024 * 1024,
        'uboot_offset': 0x000000,
        'uboot_max_size': 0x090000,
        'zimage_offset': 0x090000,
        'zimage_max_size': 0x300000,
        'rdbin_offset': 0x390000,
        'rdbin_max_size': 0x440000,
        'vendor_offset': 0x7D0000,
        'vendor_size': 0x10000,
        'dts_offset': 0x7E0000,
        'dts_size': 0x10000,
        'fis_offset': 0x7F0000,
        'bootargs': 'root=/dev/md0 rw syno_hw_version=DS212pv10 console=ttyS0,115200 ip=off ihd_num=2 netif_num=1 ip=off initrd=0x2000040,4M',
    },
    'DS211+': {
        'name': 'DS211+',
        'hw_version': 'DS211pv10',
        'flash_size': 8 * 1024 * 1024,
        'uboot_offset': 0x000000,
        'uboot_max_size': 0x090000,
        'zimage_offset': 0x090000,
        'zimage_max_size': 0x300000,
        'rdbin_offset': 0x390000,
        'rdbin_max_size': 0x440000,
        'vendor_offset': 0x7D0000,
        'vendor_size': 0x10000,
        'dts_offset': 0x7E0000,
        'dts_size': 0x10000,
        'fis_offset': 0x7F0000,
        'bootargs': 'root=/dev/md0 rw syno_hw_version=DS211pv10 console=ttyS0,115200 ip=off ihd_num=1 netif_num=1 ip=off initrd=0x2000040,4M',
    },
    'DS210+': {
        'name': 'DS210+',
        'hw_version': 'DS210pv10',
        'flash_size': 8 * 1024 * 1024,
        'uboot_offset': 0x000000,
        'uboot_max_size': 0x090000,
        'zimage_offset': 0x090000,
        'zimage_max_size': 0x300000,
        'rdbin_offset': 0x390000,
        'rdbin_max_size': 0x440000,
        'vendor_offset': 0x7D0000,
        'vendor_size': 0x10000,
        'dts_offset': 0x7E0000,
        'dts_size': 0x10000,
        'fis_offset': 0x7F0000,
        'bootargs': 'root=/dev/md0 rw syno_hw_version=DS210pv10 console=ttyS0,115200 ip=off ihd_num=1 netif_num=1 ip=off initrd=0x2000040,4M',
    },
}

DEFAULT_PATHS = {
    'uboot': [
        'uboot_{hw_version}.bin',
        'uboot.bin',
        'DSM_{model}_*/uboot_{hw_version}.bin',
        'DSM_{model}_*/uboot.bin',
    ],
    'zimage': [
        'zImage',
        'DSM_{model}_*/zImage',
    ],
    'rdbin': [
        'rd.bin',
        'DSM_{model}_*/rd.bin',
    ],
    'vendor': [
        'vender.img',
        'vendor.img',
    ],
    'dts': [
        'dtbdump_3.dtb',
        'dtb.bin',
        '*.dtb',
    ],
}

class SynologyFlashTool:
    def __init__(self, model, base_path='.'):
        self.model = model
        self.base_path = Path(base_path)
        self.platform = PLATFORMS.get(model)
        
        if not self.platform:
            raise ValueError(f"Unknown model: {model}. Use --list-models to see available models.")
        
        self.files = {}
        
    def find_file(self, patterns):
        """Find file using patterns"""
        for pattern in patterns:
            pattern = pattern.format(
                model=self.model.replace('+', 'p').replace(' ', ''),
                hw_version=self.platform['hw_version']
            )
            
            for path in self.base_path.glob(pattern):
                if path.is_file():
                    return path
            
            # Try without replacing
            for path in self.base_path.glob(pattern):
                if path.is_file():
                    return path
        return None
    
    def find_all_files(self):
        """Find all required files"""
        print(f"\n[*] Looking for files for {self.model} ({self.platform['hw_version']})...")
        
        for file_type, patterns in DEFAULT_PATHS.items():
            path = self.find_file(patterns)
            if path:
                self.files[file_type] = path
                print(f"  [+] Found {file_type}: {path.name}")
            else:
                print(f"  [!] {file_type} not found (will use empty/placeholder)")
                
    def load_file(self, file_type, default_size=0):
        """Load file or return zeros"""
        if file_type in self.files:
            with open(self.files[file_type], 'rb') as f:
                return f.read()
        return bytearray(default_size)
    
    def create_vendor(self, mac, serial_number, model_id='DS213p'):
        """Create vendor partition"""
        vendor = bytearray(self.platform['vendor_size'])
        
        # Parse MAC address
        mac_bytes = bytes.fromhex(mac.replace(':', '').replace('-', ''))
        if len(mac_bytes) != 6:
            raise ValueError(f"Invalid MAC address: {mac}")
        
        # MAC at offset 0 (6 bytes)
        vendor[0:6] = mac_bytes
        
        # Model ID at offset 4 - but don't overwrite MAC!
        # The model_id is typically in the extra bytes of MAC or separate
        # Looking at original: MAC + flag byte + zeros + SN at 0x20
        # Let's use the byte at offset 6 for checksum only
        
        # Calculate checksum (sum of first 6 bytes)
        checksum = sum(mac_bytes) & 0xFF
        vendor[6] = checksum
        
        # Serial number at offset 0x20 (32)
        sn = serial_number.encode('ascii')[:11]
        vendor[0x20:0x20+len(sn)] = sn
        
        # Default CHK=999 at offset 0x30
        vendor[0x30:0x38] = b',CHK=999'
        
        print(f"  [*] Vendor: MAC={mac}, SN={serial_number}, CHK=0x{checksum:02x}")
        
        return vendor
    
    def create_flash_image(self, output, mac=None, serial_number=None):
        """Create complete flash image"""
        self.find_all_files()
        
        # Get platform config
        p = self.platform
        
        # Create empty flash
        flash = bytearray(p['flash_size'])
        
        # Load and write u-boot
        uboot = self.load_file('uboot', p['uboot_max_size'])
        if len(uboot) > p['uboot_max_size']:
            print(f"  [!] WARNING: uboot too large ({len(uboot)} > {p['uboot_max_size']})")
            uboot = uboot[:p['uboot_max_size']]
        flash[p['uboot_offset']:p['uboot_offset']+len(uboot)] = uboot
        print(f"  [*] Written uboot: {len(uboot)} bytes at 0x{p['uboot_offset']:06x}")
        
        # Load and write zImage
        zimage = self.load_file('zimage', p['zimage_max_size'])
        if len(zimage) > p['zimage_max_size']:
            print(f"  [!] WARNING: zImage too large ({len(zimage)} > {p['zimage_max_size']})")
            zimage = zimage[:p['zimage_max_size']]
        flash[p['zimage_offset']:p['zimage_offset']+len(zimage)] = zimage
        print(f"  [*] Written zImage: {len(zimage)} bytes at 0x{p['zimage_offset']:06x}")
        
        # Load and write rd.bin
        rdbin = self.load_file('rdbin', p['rdbin_max_size'])
        if len(rdbin) > p['rdbin_max_size']:
            print(f"  [!] WARNING: rd.bin too large ({len(rdbin)} > {p['rdbin_max_size']})")
            rdbin = rdbin[:p['rdbin_max_size']]
        flash[p['rdbin_offset']:p['rdbin_offset']+len(rdbin)] = rdbin
        print(f"  [*] Written rd.bin: {len(rdbin)} bytes at 0x{p['rdbin_offset']:06x}")
        
        # Create vendor if MAC and SN provided
        if mac and serial_number:
            model_id = self.model.replace('+', 'p')
            vendor = self.create_vendor(mac, serial_number, model_id)
        else:
            vendor = self.load_file('vendor', p['vendor_size'])
            print(f"  [*] Using existing vendor file")
            
        flash[p['vendor_offset']:p['vendor_offset']+len(vendor)] = vendor
        
        # Load and write DTB
        dtb = self.load_file('dts', p['dts_size'])
        if len(dtb) > p['dts_size']:
            print(f"  [!] WARNING: DTB too large ({len(dtb)} > {p['dts_size']})")
            dtb = dtb[:p['dts_size']]
        flash[p['dts_offset']:p['dts_offset']+len(dtb)] = dtb
        print(f"  [*] Written DTB: {len(dtb)} bytes at 0x{p['dts_offset']:06x}")
        
        # Write output file
        with open(output, 'wb') as f:
            f.write(flash)
            
        print(f"\n[+] Flash image created: {output}")
        print(f"    Size: {len(flash)} bytes ({len(flash)/(1024*1024):.1f} MB)")
        
        return output
    
    def extract_vendor_info(self, flash_file):
        """Extract vendor information from flash image"""
        with open(flash_file, 'rb') as f:
            flash = f.read()
            
        p = self.platform
        vendor_offset = p['vendor_offset']
        vendor = flash[vendor_offset:vendor_offset + p['vendor_size']]
        
        mac = vendor[0:6]
        mac_str = ':'.join(f'{b:02x}' for b in mac)
        checksum = vendor[6]
        serial = vendor[0x20:0x20+11].decode('ascii', errors='replace').strip('\x00')
        
        print(f"\n[*] Vendor Information from {flash_file}:")
        print(f"    MAC: {mac_str}")
        print(f"    Serial: {serial}")
        print(f"    Checksum: 0x{checksum:02x}")
        
        # Verify checksum
        expected = sum(mac) & 0xFF
        if checksum == expected:
            print(f"    Checksum: VALID")
        else:
            print(f"    Checksum: INVALID (expected 0x{expected:02x})")
            
        return {
            'mac': mac_str,
            'serial': serial,
            'checksum': checksum,
        }
    
    def create_tftp_assets(self, output_dir):
        """Create files for TFTP recovery"""
        self.find_all_files()
        
        output = Path(output_dir)
        output.mkdir(parents=True, exist_ok=True)
        
        p = self.platform
        
        # Copy zImage
        zimage = self.load_file('zimage', p['zimage_max_size'])
        (output / 'zImage').write_bytes(zimage)
        
        # Copy rd.bin  
        rdbin = self.load_file('rdbin', p['rdbin_max_size'])
        (output / 'rd.bin').write_bytes(rdbin)
        
        print(f"\n[+] TFTP assets created in: {output}")
        print(f"    zImage: {len(zimage)} bytes")
        print(f"    rd.bin: {len(rdbin)} bytes")
        
        return output


def list_models():
    """List available models"""
    print("\nAvailable Synology models:")
    print("-" * 40)
    for name, config in PLATFORMS.items():
        print(f"  {name:12} - {config['name']} ({config['hw_version']})")
        print(f"              Flash: {config['flash_size']/(1024*1024):.0f}MB")


def interactive_mode():
    """Interactive configuration"""
    print("\n=== Synology Flash Tool - Interactive Mode ===\n")
    
    list_models()
    
    print("\n[1] Select model")
    for i, name in enumerate(PLATFORMS.keys(), 1):
        print(f"    {i}. {name}")
    
    while True:
        try:
            choice = int(input("\nSelect model number: "))
            if 1 <= choice <= len(PLATFORMS):
                model = list(PLATFORMS.keys())[choice - 1]
                break
        except ValueError:
            pass
        print("Invalid choice, try again.")
    
    tool = SynologyFlashTool(model)
    tool.find_all_files()
    
    print("\n[2] Configuration")
    mac = input("MAC address (e.g. 00113218139E): ").strip() or None
    sn = input("Serial number (e.g. CAL1N10508): ").strip() or None
    
    output = f"synology_{model}_flash.bin"
    
    print("\n[3] Creating flash image...")
    tool.create_flash_image(output, mac, sn)
    
    print("\n[4] Creating TFTP assets...")
    tool.create_tftp_assets(f"tftp_{model}")
    
    print("\n=== Done! ===")


def main():
    parser = argparse.ArgumentParser(
        description='Synology Flash Tool - Create SPI flash firmware images',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --model DS213+ --mac 00113218139E --sn CAL1N10508
  %(prog)s --interactive
  %(prog)s --list-models
  %(prog)s --extract-vendor flash.bin
  %(prog)s --tftp-output tftp_recovery --model DS213+
        """
    )
    
    parser.add_argument('--model', '-m', help='Synology model (e.g., DS213+)')
    parser.add_argument('--mac', '-a', help='MAC address (e.g., 00113218139E)')
    parser.add_argument('--sn', '-s', help='Serial number (e.g., CAL1N10508)')
    parser.add_argument('--output', '-o', help='Output file name')
    parser.add_argument('--base-path', '-b', default='.', help='Base path to search for files')
    parser.add_argument('--list-models', '-l', action='store_true', help='List available models')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive mode')
    parser.add_argument('--extract-vendor', '-e', metavar='FILE', help='Extract vendor info from flash image')
    parser.add_argument('--tftp-output', '-t', metavar='DIR', help='Create TFTP recovery assets')
    parser.add_argument('--version', '-v', action='version', version='%(prog)s 1.0')
    
    args = parser.parse_args()
    
    if args.list_models:
        list_models()
        return 0
        
    if args.extract_vendor:
        if not args.model:
            print("Error: --model required for vendor extraction")
            return 1
        tool = SynologyFlashTool(args.model, args.base_path)
        tool.extract_vendor_info(args.extract_vendor)
        return 0
        
    if args.tftp_output:
        if not args.model:
            print("Error: --model required for TFTP assets")
            return 1
        tool = SynologyFlashTool(args.model, args.base_path)
        tool.create_tftp_assets(args.tftp_output)
        return 0
        
    if args.interactive:
        interactive_mode()
        return 0
        
    if not args.model:
        parser.print_help()
        return 1
        
    # Validate MAC if provided
    if args.mac:
        mac_clean = args.mac.replace(':', '').replace('-', '')
        if len(mac_clean) != 12:
            print(f"Error: Invalid MAC address format: {args.mac}")
            return 1
            
    # Validate SN if provided
    if args.sn:
        if len(args.sn) > 11:
            print(f"Error: Serial number too long (max 11 chars): {args.sn}")
            return 1
    
    output = args.output or f"synology_{args.model.replace('+', 'p')}_flash.bin"
    
    print(f"\n=== Synology Flash Tool ===")
    print(f"Model: {args.model}")
    print(f"MAC: {args.mac or 'default'}")
    print(f"SN: {args.sn or 'default'}")
    print(f"Output: {output}")
    
    try:
        tool = SynologyFlashTool(args.model, args.base_path)
        tool.create_flash_image(output, args.mac, args.sn)
        
        # Also create TFTP assets
        tftp_dir = f"tftp_{args.model.replace('+', 'p')}"
        tool.create_tftp_assets(tftp_dir)
        
        print("\n=== Done! ===")
        return 0
        
    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
