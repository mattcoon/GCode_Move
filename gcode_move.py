# gcode_move by Matthew Coon
# written to support easy manipulation of GCODE for 3d printing or laser cutting

from pathlib import Path
import re
import sys

# cAxis is a class with all known axises to be adjusted. these include the expected XYZ and e for extruder, f for
# feedrate and s for fanspeed
class cAxis:
    def __init__(self,x=0,y=0,z=0,f=0,e=0,s=0) -> None:
        self.x = x
        self.y = y 
        self.z = z
        self.f = f
        self.e = e
        self.s = s
    def __add__(self,addr):
        return cAxis(self.x+addr.x, self.y+addr.y, self.z+addr.z, self.f+addr.f, self.e+addr.e, self.s+addr.s)
    def __sub__(self,addr):
        return cAxis(self.x-addr.x, self.y-addr.y, self.z-addr.z, self.f-addr.f, self.e-addr.e, self.s-addr.s)
    def min(self,other):
        self.x = min(self.x,other.x)
        self.y = min(self.y,other.y)
        self.z = min(self.z,other.z)
        self.f = min(self.f,other.f)
        self.e = min(self.e,other.e)
        self.s = min(self.s,other.s)
    def copy(self,other):
        self.x = other.x
        self.y = other.y
        self.z = other.z
        self.f = other.f
        self.e = other.e
        self.s = other.s
    def setXYZ(self,value):
        self.x = value
        self.y = value
        self.z = value

def rotate (position,rotation,offsets, limits):
    axis = position[0:1]
    distance = float(findFloat(position,axis).groups()[0])
    if rotation == 90:
        # CW rotation: x=y, y=maxX-x: LL corner is UL
        if axis == 'Y':
            axis = 'X'
            distance = offsets.x + distance - offsets.y
        elif axis == 'X':
            axis = 'Y'
            distance = offsets.y + limits.x - distance
    elif rotation == -90:
        # CCWrotation: x=maxY-y, y=x: LL corner is LR
        if axis == 'X':
            axis = 'Y'
            distance = offsets.y + distance - offsets.x
        elif axis== 'Y':
            axis = 'X'
            distance = offsets.x + limits.y - distance
    elif rotation == 180:
        # 180 rotation: x=maxX-x,y=maxY-y: LL corner is UR
        if axis == 'X':
            distance = offsets.x + limits.x - distance
        elif axis == 'Y':
            distance = offsets.y + limits.y - distance
    else:
        #else do nothing. assume 0. must be caught
        pass
    return str(axis+str(distance))


def findFloat (str,param):
    reSearch = re.compile(param+'(\d*.\d*)')
    parts = reSearch.search(str)
    return parts

def findInt (str,param):
    reSearch = re.compile(param+'(\d*)')
    parts = reSearch.search(str)
    return parts

# def rotate(strPosition,orginalLimit):
    # strPostion is the G0 axis string, 'X12.23'. function returns corrected string after rotation


# ProcessFile is the core workhorse to pull in each line, parse and manipulate as needed and option write out
def ProcessFile (filenameIn, filenameOut):
    global cAxis
    global scale
  
    bLaserOn=False
    delta = offset

    initialMin = cAxis()
    initialMin.copy(LimMax)
    initialMax = cAxis()
    finalMin = cAxis()
    finalMin.copy(LimMax)
    finalMax = cAxis()

    if not bAnalyseOnly:
        # only open output file if no in analysis mode
        fileOut = open(Path(filenameOut),'w')
        print("Writing to "+filenameOut)

    with open(Path(filenameIn),'r') as fileIn:
        # Find offset with finalMin
        for line in fileIn:
            commandComment = line.split(';')
            # everything after the ; is a comment. only parse before the ;
            line = commandComment[0]
            if line[0:1] == 'G' or line[0:1] == 'M':
                for axis in ['X','Y','Z','F','S']:
                    axisValue = findFloat(line,axis)
                    if axisValue:
                        position = float(axisValue.groups()[0])
                        match axis:
                            case 'X':
                                initialMin.x = min(initialMin.x,position)
                                initialMax.x = max(initialMax.x,position)
                            case 'Y':
                                initialMin.y = min(initialMin.y,position)
                                initialMax.y = max(initialMax.y,position)
                            case 'Z':
                                initialMin.z = min(initialMin.z,position)
                                initialMax.z = max(initialMax.z,position)
                            case "F":
                                initialMin.f = min(initialMin.f,position)
                                initialMax.f = max(initialMax.f,position)
                            case "S":
                                initialMin.s = min(initialMin.s,position)
                                initialMax.s = max(initialMax.s,position)
        # if no positions found in axis, min will be max, reset that
        initialMin.min(initialMax)
        if 'bCleanMode' in globals():
            # calculate deltas based on requested location and found min values
            # add back any tool offset if defined
            delta = delta - initialMin + toolOffset
        if 'tarDepth' in globals():
            scale.y = tarDepth/(initialMax.y-initialMin.y)
            # if width not specified scale proportionally
            if 'tarWidth' not in globals():
                scale.x = scale.y
        if 'tarWidth' in globals():
            scale.x = tarWidth/(initialMax.x-initialMin.x)
            # if depth not specified scale proportionally
            if 'tarDepth' not in globals():
                scale.y = scale.x

        fileIn.seek(0)
        # reset file if offset searched

        for line in fileIn:
            commandComment = line.split(';')
            # everything after the ; is a comment. only parse before the ;
            command = commandComment[0]
            comment = ''
            if len(commandComment) > 1:
                comment = ';' + commandComment[1]
            linesplit = command.split()
            lineNew = command
            if linesplit:
                #check if command is a move
                if linesplit[0] == 'G0' or linesplit[0] == 'G1':
                    for parts in linesplit:
                        if parts[0:1] == 'G': # G0 G1 Handler
                            # handle laser by making g0 g1 and threshold to completely turn off laser
                            if bLaserMode: # use G0 for unpowered laser moves, G1 for powered
                                if bLaserOn:
                                    lineNew = 'G1'
                                else:
                                    lineNew = 'G0'
                            else: #leave G0/G1 alone as pass thru
                                lineNew = parts
                        else: # handle all other parts of move line
                            if rotation != 0:
                                # rotation done before scaling and offsetting and axis to simplify handling of parameter
                                parts = rotate(parts,rotation,initialMin,initialMax)
                            axis = parts[0:1]
                            valuestr = findFloat(parts,axis)
                            if valuestr:
                                currentPos = float(valuestr.groups()[0])
                            else:
                                currentPos = 0
                            match axis:
                                case 'X':
                                    currentPos = Scale(currentPos-initialMin.x,scale.x,0,LimMax.x)+initialMin.x
                                    currentPos = Transpose(currentPos,delta.x,0,LimMax.x)
                                    lineNew+= ' {0:s}{1:.6f}'.format(axis,currentPos)
                                    finalMax.x = max(currentPos,finalMax.x)
                                    finalMin.x = min(currentPos,finalMin.x)
                                case 'Y':
                                    currentPos = Scale(currentPos-initialMin.y,scale.y,0,LimMax.y)+initialMin.y
                                    currentPos = Transpose(currentPos,delta.y,0,LimMax.y)
                                    lineNew+= ' {0:s}{1:.6f}'.format(axis,currentPos)
                                    finalMax.y = max(currentPos,finalMax.y)
                                    finalMin.y = min(currentPos,finalMin.y)
                                case 'Z':
                                    currentPos = Scale(currentPos-initialMin.z,scale.z,0,LimMax.z)+initialMin.z
                                    currentPos = Transpose(currentPos,delta.z,0,LimMax.z)
                                    lineNew+= ' {0:s}{1:.6f}'.format(axis,currentPos)
                                    finalMax.z = max(currentPos,finalMax.z)
                                    finalMin.z = min(currentPos,finalMin.z)
                                case 'F':
                                    currentPos = Scale(currentPos,scale.f,0,LimMax.f)
                                    lineNew+= ' '+axis+str(currentPos)
                                    finalMax.f = max(currentPos,finalMax.f)
                                    finalMin.f = min(currentPos,finalMin.f)
                                case 'E':
                                    currentPos = Scale(currentPos,scale.e,-LimMax.e,LimMax.e)
                                    lineNew+= ' '+axis+str(currentPos)
                                case 'S':
                                    currentPos = Scale(currentPos,scale.s,0,LimMax.s)
                                    lineNew+= ' '+axis+str(currentPos)
                                    finalMax.s = max(currentPos,finalMax.s)
                                    finalMin.s = min(currentPos,finalMin.s)
                    lineNew+='\n'
                #check for Laser (fan PWM) on command M106 or M3
                if linesplit[0] == "M106" or linesplit[0] == "M3":
                        #fanSpeed = int(findInt(linesplit[1],'S').groups()[0])
                        #if fanSpeed < minOn:
                        #    line = "M107 ; output limited\n"
                        #    bLaserOn=False
                        #else:
                    # TODO: update if translating M3 to M106 etc
                    lineNew = ""
                    # else write line as is.
                    for parts in linesplit:
                        axis = parts[0:1]
                        valuestr = findInt(parts,axis)
                        match axis:
                            case 'S':
                                if valuestr:
                                    currentSpd = int(valuestr.groups()[0])
                                else:
                                    currentSpd = 0
                                if currentSpd < minOn:
                                    line = "M107 ; output limited\n"
                                    bLaserOn=False
                                else:
                                    currentSpd = Scale(currentSpd,scale.s,0,LimMax.s)
                                    lineNew+= ' '+axis+str(int(currentSpd))
                                    finalMax.s = max(currentSpd,finalMax.s)
                                    finalMin.s = min(currentSpd,finalMin.s)
                            case _:
                                lineNew+= parts
                    bLaserOn=True
                    lineNew+='\n'
                # check for laser (fan PWM) off commadn
                if linesplit[0] == "M107":
                    bLaserOn = False
            line = lineNew+comment
            # write only if not in analyse only mode
            if bAnalyseOnly == False:
                fileOut.write(line)
        # fix any statistics where no change in axis. min will still be at max
        finalMin.min(finalMax)
        # output statistics 
        print('Scaled by x:{0:.2f} y:{1:.2f}.'.format(scale.x,scale.y))
        print('Scaled feedrate:{0:2f}  laser:{1:2f}'.format(scale.f,scale.s))
        print('Initial')
        print('Min X: {0:.2f} Max X: {1:.2f} width: {2:.2f}'.format(initialMin.x, initialMax.x, initialMax.x-initialMin.x))
        print('Min Y: {0:.2f} Max Y: {1:.2f} depth: {2:.2f}'.format(initialMin.y, initialMax.y, initialMax.y-initialMin.y))
        print('Min Z: {0:.2f} Max Z: {1:.2f} height: {2:.2f}'.format(initialMin.z, initialMax.z, initialMax.z-initialMin.z))
        print('feedrate    Min: {0:2f} Max: {1:2f}'.format(initialMin.f,initialMax.f))
        print('Speed/laser Min: {0:2f} Max: {1:2f}'.format(initialMin.s,initialMax.s))
        print('Final')
        print('Min X: {0:.2f} Max X: {1:.2f} width: {2:.2f}'.format(finalMin.x, finalMax.x, finalMax.x-finalMin.x))
        print('Min Y: {0:.2f} Max Y: {1:.2f} depth: {2:.2f}'.format(finalMin.y, finalMax.y, finalMax.y-finalMin.y))
        print('Min Z: {0:.2f} Max Z: {1:.2f} height: {2:.2f}'.format(finalMin.z, finalMax.z, finalMax.z-finalMin.z))
        print('feedrate    Min: {0:2f} Max: {1:2f}'.format(finalMin.f,finalMax.f))
        print('Speed/laser Min: {0:2f} Max: {1:2f}'.format(finalMin.s,finalMax.s))

def Transpose (position,offset,limLow,limHi):
    return round(max(limLow,min(limHi,position+offset)),6)

def Scale (position,scale,limLow,LimHi):
    return round(max(limLow,min(LimHi,position*scale)),6)
    
offset = cAxis(0,0,0)
toolOffset = cAxis(0,0,0)
defaultScale = 1
scale = cAxis(defaultScale,defaultScale,defaultScale,defaultScale,defaultScale,defaultScale)
rotation = 0
LimMax = cAxis (1220,900,250,50000,50000,255)
LimMin = cAxis (0, 0, 0)
minOn = 0
filenameIn = ''
filenameOut = ''
bAnalyseOnly = False
bLaserMode = False


if len(sys.argv) > 1:
    for argument in sys.argv:
        keyword = argument[0:2]
        userData = argument[2:len(argument)]
        match keyword:
            case '-i':  # input file
                filenameIn = userData
            case '-o':  # output file
                filenameOut = userData
            case '-X':  # X offset
                offset.x = float(userData)
            case '-Y':  # Y offset
                offset.y = float(userData)
            case '-Z':  # Z offset
                offset.z = float(userData)
            case '-c':  # clean offset base on min gcode value
                # set offset based on absolute
                bCleanMode = True
                if len(userData) > 0:
                    if userData[0:1] == 'X':
                        toolOffset.x = float(userData[1:len(userData)])
                    if userData[0:1] == 'Y':
                        toolOffset.y = float(userData[1:len(userData)])
            case '-F':  # Feedrate scaling
                scale.f = float(userData)
            case '-E':  # Extruder scaling
                scale.e = float(userData)
            case '-S':  # Speed scaling for FAN/Laser.
                scale.s = float(userData)
            case '-h':  # help
                print('gcode_move -iInputFile -oOutputFile -Xoffset -Yoffset -Zoffset -FFeedrate -EExtruderrate')
                print('           -Sfanspeed -aAnalyseOnly -lLaserlowerLimit -sScale -cClean -wWidth -dDepth -rRotate')
                print('Feedrates are in percent. Offset in mm.')
                print('laser affects fanspeed 0-255 before turning off laser and puts in laser mode. ')
                print('S option will scale all S parameters used in Gx M3, and M106 commands my multiplying')
                print('G1 while laser is off will become G0. use -l0 to keep laser PWMs but use G1/G0 substitutions')
                print('XYZ scaling will treat as a mulitpler for any present components while keeping offsets. Note for 3d')
                print('the first line is in scope and will prevent use of offset for scaling')
                print('Clean mode removes all offsets and sets object to 0 offset.')
                print('If cleanmode and offset used, will set object to absolute locations')
                print('Width and Depth cannot be used together with Scaling.')
                print('Rotate take 90 for CW, 180, or -90 for CCW rotations only')
                quit()
            case '-a':  # analysis and report only / no output
                bAnalyseOnly = True
                print('Analysis Only Mode - no output')
            case '-l':  # laser mode with min on value
                minOn = int(userData)
                bLaserMode = True
            case '-s':  # scale X and Y and Z
                defaultScale = (float(userData))
                scale.setXYZ(defaultScale)
            case '-w':  # width of output image
                tarWidth = float(userData)
            case '-d':  # depth/height of output image
                tarDepth = float(userData)
            case '-r':  # rotate image
                if userData == '0':
                    rotation = 0
                elif userData == '90':
                    rotation = 90
                elif userData == '-90':
                    rotation = -90
                elif userData == '180':
                    rotation = 180
                else:
                    print('Rotation of {} not allowed.'.format(userData))
                    quit()
                print('Image rotation {}'.format(rotation))
else:
    # No arguments passed. walk user thru common inputs
    print('no args - defaults in ( )')
    userIn = input('X Offset ({}):'.format(str(offset.x)))
    if userIn != '': offset.x = float(userIn) 
    userIn = input('Y Offset ({}):'.format(str(offset.y)))
    if userIn != '': offset.y = float(userIn) 
    userIn = input('Z Offset ({}):'.format(str(offset.z)))
    if userIn != '': offset.z = float(userIn) 
    userIn = input('XYZ Scaling ({}):'.format(str(defaultScale)))
    if userIn != '': scale.setXYZ(float(userIn))
    userIn = input('Feed Rate scaling ({}):'.format(str(scale.f)))
    if userIn != '': scale.f = float(userIn) 
    userIn = input('Extruder Rate scaling ({}):'.format(str(scale.e)))
    if userIn != '': scale.e = float(userIn) 
    userIn = input('Fan/laser speed scaling ({}):'.format(str(scale.s)))
    if userIn != '': scale.s = float(userIn) 
    userIn = input('Max X value ({}):'.format(str(LimMax.x)))
    if userIn != '': LimMax.x = float(userIn) 
    userIn = input('Max Y value ({}):'.format(str(LimMax.y)))
    if userIn != '': LimMax.y = float(userIn) 
    userIn = input('Max Z value ({}):'.format(str(LimMax.z)))
    if userIn != '': LimMax.z = float(userIn) 
    userIn = input('Max feedrate ({}):'.format(str(LimMax.f)))
    if userIn != '': LimMax.f = float(userIn) 
    userIn = input('Max Extruder ({}):'.format(str(LimMax.e)))
    if userIn != '': LimMax.e = float(userIn) 
    userIn = input('Laser PWM off limit ({}):'.format(str(minOn)))
    if userIn != '': minOn = int(userIn) 


if filenameIn == '':
    filenameIn = input('Input filename:')
if filenameOut == '':
    filenameOut = 'out{0}_{1}deg_{2}x_x{3}y{4}'.format(filenameIn,rotation,defaultScale,offset.x,offset.y)
if defaultScale!= 1 and ('tarDepth' in globals() or 'tarWidth' in globals()):
    print('scaling and widith or depth cannot be used together. skipping scaling')
    #skipping happens automatically as fixed width and depth will overwrite any fixed scaler

ProcessFile(filenameIn,filenameOut)
