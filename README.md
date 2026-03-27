# Synology Flash Tool

A tool for automatically creating firmware images for SPI memory on Synology DS devices.

## Supported Models

- DS213+
- DS213
- DS212+
- DS212
- DS211+
- DS210+

## Requirements

- Python 3.6+
- Firmware files (zImage, rd.bin, uboot, dtb, vendor)

## Installation

```bash
# Clone or download
git clone <repo-url>
cd synology

# Check available models
python synology_flash_tool.py --list-models
```

## Usage

### Interactive mode (recommended)

```bash
python synology_flash_tool.py --interactive
```

### Basic Usage

```bash
python synology_flash_tool.py \
--model DS213+ \
--mac 00113218139B \
--sn CAL1N10509 \
--output DS213+_flash.bin
```

### Extract information from an existing flash

```bash
python synology_flash_tool.py \
--model DS213+ \
--extract-vendor backup_flash.bin
```

### Create TFTP recovery files

```bash
python synology_flash_tool.py \
--model DS213+ \
--tftp-output tftp_recovery
```

## Flash image structure (8MB)

| Offset | Size | Description |
|-----------|-----------|----------------|
| 0x000000 | 576KB | U-boot |
| 0x090000 | 3MB | zImage(kernel)|
| 0x390000 | 4.25MB | rd.bin(initrd)|
| 0x7D0000 | 64KB | Vendor (MAC/SN)|
| 0x7E0000 | 64KB | DTB |
| 0x7F0000 | 64KB | FIS directory |

## Firmware Upload Methods

### Method 1: SPI Programmer (Recommended)

The safest method - requires an SPI programmer (CH341A, Raspberry Pi, etc.)

```bash
# Read current flash (backup)
flashrom -p ch341a_spi -r backup_flash.bin

# Upload new firmware
flashrom -p ch341a_spi -w DS213+_flash.bin

# Verification
flashrom -v DS213+_flash.bin -p ch341a_spi
```

#### Programmer Pinout (M25P64)

```
Programmer → Flash
──────────────────
VCC → pin 8 (some models 3.3V, others 1.8V - check!)
GND → pin 7
MOSI → pin 5
MISO → pin 2
SCK → pin 6
CS → pin 1
```

### Method 2: TFTP Recovery (via TTL console)

If the device boots into U-boot:

1. Connect the TTL console (115200 8N1)
2. Connect the Ethernet
3. Configure the TFTP server (place the files from the `tftp_DS213p` folder)

```
Press Ctrl+C to abort autoboot in 3 seconds
=> setenv ipaddr 192.168.1.100
=> setenv serverip 192.168.1.50
=> tftpboot 0x1000000 zImage
=> tftpboot 0x2000000 rd.bin
=> sf probe 0
=> sf read c00000 7E0000 10000
=> bootm 1000000 2000000 c00000
```

### Method 3: Upload the full image via U-boot

```
=> tftpboot 0x1000000 DS213+_flash.bin
=> sf probe 0
=> sf write 0x1000000 0x0 $filesize
```

## Vendor Partition Structure

```
Offset 0x00: MAC address (6 bytes)
Offset 0x04: Model ID (4 bytes) - e.g., "DS213p"
Offset 0x06: Checksum (1 byte) - the sum of the first 6 bytes
Offset 0x20: Serial number (11 bytes)
Offset 0x30: ",CHK=999" (default)
```

## Troubleshooting

### "Wrong Ramdisk Image Format"
- Make sure you're using the correct addresses:
- zImage: 0x1000000
- rd.bin: 0x2000000
- dtb: 0xc00000
- Use the command: `bootm 0x1000000 0x2000000 0xc00000`

### "Bad trap at PC"
- Incorrect kernel/ramdisk version
- Check if the versions are compatible

### LEDs in incorrect state
- Check the MAC address in the vendor
- Check the checksum: `sum(bytes[0:6]) & 0xFF`

### Device does not detect disks
- Check if the DSM is loaded correctly
- Try an older DSM version

## Flashing via Raspberry Pi

```bash
# Connect flash to Raspberry Pi GPIO
# Pinout:
# MOSI -> GPIO10 (pin 19)
# MISO -> GPIO9 (pin 21)
# SCK -> GPIO11 (pin 23)
# CE0 -> GPIO8 (pin 24)
# GND -> GND (pin 25)
# VCC -> 3.3V (pin 1)

# Flash from Raspberry
sudo flashrom -p linux_spi:dev=/dev/spidev0.0,spispeed=1000 -w DS213+_flash.bin

## PAT File Format

If you only have the .pat file from the official Synology website:

```bash
# Extract the .pat file (7zip or tar)
7z x DSM_DS213+_25556.pat -o DSM_extract

# Search:
# - zImage
# - rd.bin
# - hda1.tgz (main system)
# - grub grub1.img (if needed)

## Disclaimer

This tool is intended to repair devices with corrupted firmware. Use at your own risk. I am not responsible for any damage resulting from using this tool.

## License

MIT License
