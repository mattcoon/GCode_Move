# GCode Move

A Python utility for manipulating G-code files for 3D printing and laser cutting applications. This tool allows you to transform, scale, rotate, and translate G-code commands with precise control over positioning and parameters.

## Features

- **Coordinate Transformation**: Apply X, Y, Z offsets to reposition objects
- **Scaling**: Scale objects by percentage or to specific dimensions
- **Rotation**: Rotate objects by 90°, -90°, or 180°
- **Laser Mode**: Convert between 3D printer and laser cutter G-code formats
- **Analysis Mode**: Analyze G-code files without generating output
- **Clean Mode**: Normalize positioning by removing offsets
- **Command Translation**: Convert between different G-code command formats
- **Interactive Mode**: User-friendly prompts when no arguments provided

## Installation

No installation required. Simply ensure you have Python 3.x installed and run the script directly.

## Usage

### Command Line Interface

```bash
python gcode_move.py [options]
```

### Basic Examples

#### 1. Simple Offset (Move object 10mm right, 5mm back)
```bash
python gcode_move.py -iinput.gcode -ooutput.gcode -X10 -Y5
```

#### 2. Scale Object to 50% Size
```bash
python gcode_move.py -iinput.gcode -ooutput.gcode -s0.5
```

#### 3. Rotate Object 90 Degrees Clockwise
```bash
python gcode_move.py -iinput.gcode -ooutput.gcode -r90
```

#### 4. Scale to Specific Dimensions (50mm width)
```bash
python gcode_move.py -iinput.gcode -ooutput.gcode -w50
```

### Advanced Examples

#### 5. Convert 3D Printer G-code to Laser Cutter Format
```bash
python gcode_move.py -iprint_file.gcode -olaser_file.gcode -l128 -TM3
```
- `-l128`: Enable laser mode with minimum power of 128
- `-TM3`: Translate fan commands (M106) to laser commands (M3)

#### 6. Clean Mode with Tool Offset
```bash
python gcode_move.py -iinput.gcode -ooutput.gcode -c -X5 -Y3
```
Removes all existing offsets and positions object at X5, Y3

#### 7. Z-Axis to Laser Power Conversion
```bash
python gcode_move.py -iinput.gcode -ooutput.gcode -2z5 -l200
```
Converts Z-axis movements to laser power control (Z below 5mm = laser on at power 200)

#### 8. Multiple Transformations Combined
```bash
python gcode_move.py -iinput.gcode -ooutput.gcode -X20 -Y10 -s0.75 -r180 -F1.2
```
- Move 20mm right, 10mm back
- Scale to 75% size  
- Rotate 180 degrees
- Increase feedrate by 20%

#### 9. Analysis Only (No Output File)
```bash
python gcode_move.py -iinput.gcode -a
```
Analyzes the file and displays statistics without creating an output file

### Interactive Mode

If no arguments are provided, the script enters interactive mode with user prompts:

```bash
python gcode_move.py
```

The script will ask for:
- X, Y, Z offsets
- Scaling factors
- Feedrate scaling
- Machine limits
- Input and output filenames

## Command Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `-i` | Input filename | `-iinput.gcode` |
| `-o` | Output filename | `-ooutput.gcode` |
| `-X` | X-axis offset (mm) | `-X10.5` |
| `-Y` | Y-axis offset (mm) | `-Y-5.2` |
| `-Z` | Z-axis offset (mm) | `-Z2.0` |
| `-s` | XYZ scale factor | `-s0.5` |
| `-w` | Target width (mm) | `-w100` |
| `-d` | Target depth (mm) | `-d50` |
| `-r` | Rotation (0, 90, -90, 180) | `-r90` |
| `-F` | Feedrate scale factor | `-F1.5` |
| `-E` | Extruder scale factor | `-E0.8` |
| `-1` | Speed/laser scale factor | `-11.2` |
| `-l` | Laser mode (min power) | `-l100` |
| `-c` | Clean mode | `-c` or `-cX5Y3` |
| `-T` | Command translation | `-TM3` or `-TM106` |
| `-a` | Analysis only | `-a` |
| `-2` | Z-to-laser conversion | `-2z5` |
| `-h` | Help/usage | `-h` |

## Output

The script provides detailed statistics about the transformation:

```
Scaled by x:0.75 y:0.75.
Scaled feedrate:1.20  laser:1.00
Initial
Min X: 0.00 Max X: 100.00 width: 100.00
Min Y: 0.00 Max Y: 80.00 depth: 80.00
Min Z: 0.00 Max Z: 5.00 height: 5.00
Final  
Min X: 20.00 Max X: 95.00 width: 75.00
Min Y: 10.00 Max Y: 70.00 depth: 60.00
Min Z: 0.00 Max Z: 5.00 height: 5.00
```

## Machine Limits

Default machine limits (can be overridden in interactive mode):
- X: 1220mm
- Y: 900mm  
- Z: 250mm
- Feedrate: 50000 mm/min
- Laser Power: 0-255

## File Naming Convention

When no output filename is specified, the script automatically generates descriptive filenames:

```
out{input_filename}_{rotation}deg_{scale}x_x{x_offset}y{y_offset}.gcode
```

Example: `outtest.gcode_90deg_0.5x_x10.0y5.0.gcode`

## Notes

- Scaling and width/depth parameters cannot be used together
- Rotation is applied before scaling and offsetting
- The script preserves comments from the original G-code
- All coordinates are limited to machine boundaries
- Laser mode automatically converts G0/G1 commands based on laser state

## Author

Written by Matthew Coon for easy manipulation of G-code files for 3D printing and laser cutting applications.

## License

This project is open source. Feel free to use and modify as needed.