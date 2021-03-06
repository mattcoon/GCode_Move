# gcode_move by Matthew Coon
# written to support easy manipulation of GCODE for 3d printing or laser cutting
# - moving offset to object from 0,0,0
# - scaling feed, extrusion, or X,Y,Z independently
# - scale based on target width or depth
# - analysis only mode with statistics before and after modification
# - runs command line or interactive
# - rotates image by -/+90 or 180 deg

from pathlib import Path
import re
import sys

class cAxis:
    def __init__(self,x=0,y=0,z=0,f=0,e=0) -> None:
        self.x = x
        self.y = y 
        self.z = z
        self.f = f
        self.e = e
    def __add__(self,addr):
        return cAxis(self.x+addr.x, self.y+addr.y, self.z+addr.z, self.f+addr.f, self.e+addr.e)
    def __sub__(self,addr):
        return cAxis(self.x-addr.x, self.y-addr.y, self.z-addr.z, self.f-addr.f, self.e-addr.e)
    def min(self,other):
        self.x = min(self.x,other.x)
        self.y = min(self.y,other.y)
        self.z = min(self.z,other.z)
        self.f = min(self.f,other.f)
        self.e = min(self.e,other.e)
    def copy(self,other):
        self.x = other.x
        self.y = other.y
        self.z = other.z
        self.f = other.f
        self.e = other.e
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
            if line[0:1] == 'G':
                for axis in ['X','Y','Z']:
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
        
        # if no positions found in axis, min will be max, reset that
        initialMin.min(initialMax)
        if 'bCleanMode' in globals():
            # calculate deltas based on requested location and found min values
            delta -= initialMin
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
            linesplit = line.split()
            if linesplit:
                #check if command is a move
                if linesplit[0] == 'G0' or linesplit[0] == 'G1':
                    for parts in linesplit:
                        if parts[0:1] == ';':
                            #end of line / comment reached
                            break
                        if parts[0:1] == 'G':
                            # handle laser by making g0 g1 and threshold to completely turn off laser
                            if bLaserMode:
                                if bLaserOn:
                                    lineNew = 'G1'
                                else:
                                    lineNew = 'G0'
                            else:
                                #leave G0/G1 alone as pass thru
                                lineNew = parts
                        else:
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
                                case 'E':
                                    currentPos = Scale(currentPos,scale.e,-LimMax.e,LimMax.e)
                                    lineNew+= ' '+axis+str(currentPos)
                    line = lineNew+'\n'
                #check for Laser (fan PWM) on command
                if linesplit[0] == "M106":
                    fanSpeed = int(findInt(linesplit[1],'S').groups()[0])
                    if fanSpeed < minOn:
                        line = "M107 ; output limited\n"
                        bLaserOn=False
                    else:
                        # else write line as is.
                        bLaserOn=True
                # check for laser (fan PWM) off commadn
                if linesplit[0] == "M107":
                    bLaserOn = False
                # write only if not in analyse only mode
                if bAnalyseOnly == False:
                    fileOut.write(line)
        # fix any statistics where no change in axis. min will still be at max
        finalMin.min(finalMax)
        # output statistics 
        print('Scaled by x:{0:.2f} y:{1:.2f}.'.format(scale.x,scale.y))
        print('Initial')
        print('Min X: {0:.2f} Max X: {1:.2f} width: {2:.2f}'.format(initialMin.x, initialMax.x, initialMax.x-initialMin.x))
        print('Min Y: {0:.2f} Max Y: {1:.2f} depth: {2:.2f}'.format(initialMin.y, initialMax.y, initialMax.y-initialMin.y))
        print('Min Z: {0:.2f} Max Z: {1:.2f} height: {2:.2f}'.format(initialMin.z, initialMax.z, initialMax.z-initialMin.z))
        print('Final')
        print('Min X: {0:.2f} Max X: {1:.2f} width: {2:.2f}'.format(finalMin.x, finalMax.x, finalMax.x-finalMin.x))
        print('Min Y: {0:.2f} Max Y: {1:.2f} depth: {2:.2f}'.format(finalMin.y, finalMax.y, finalMax.y-finalMin.y))
        print('Min Z: {0:.2f} Max Z: {1:.2f} height: {2:.2f}'.format(finalMin.z, finalMax.z, finalMax.z-finalMin.z))

def Transpose (position,offset,limLow,limHi):
    return round(max(limLow,min(limHi,position+offset)),6)

def Scale (position,scale,limLow,LimHi):
    return round(max(limLow,min(LimHi,position*scale)),6)
    
offset = cAxis(0,0,0)
defaultScale = 1
scale = cAxis(defaultScale,defaultScale,defaultScale,defaultScale,defaultScale)
rotation = 0
LimMax = cAxis (220, 220,250,50000,50000)
LimMin = cAxis (0, 0, 0)
minOn = 0.0
filenameIn = ''
filenameOut = ''
bAnalyseOnly = False
bLaserMode = False


if len(sys.argv) > 1:
    for argument in sys.argv:
        keyword = argument[0:2]
        userData = argument[2:len(argument)]
        match keyword:
            case '-i':
                filenameIn = userData
            case '-o':
                filenameOut = userData
            case '-X':
                offset.x = float(userData)
            case '-Y':
                offset.y = float(userData)
            case '-Z':
                offset.z = float(userData)
            case '-F':
                scale.f = float(userData)
            case '-E':
                scale.e = float(userData)
            case '-h':
                print('gcode_move -iInputFile -oOutputFile -Xoffset -Yoffset -Zoffset -FFeedrate -EExtruderrate')
                print('           -aAnalyseOnly -lLaserlowerLimit -sScale -cClean -wWidth -dDepth -rRotate')
                print('Feedrates are in percent. Offset in mm.')
                print('laser affects fanspeed 0-255 before turning off laser and puts in laser mode. ')
                print('G1 while laser is off will become G0. use -l0 to keep laser PWMs but use G1/G0 substitutions')
                print('XYZ scaling will treat as a mulitpler for any present components while keeping offsets. Note for 3d')
                print('the first line is in scope and will prevent use of offset for scaling')
                print('Clean mode removes all offsets and sets object to 0 offset.')
                print('If cleanmode and offset used, will set object to absolute locations')
                print('Width and Depth cannot be used together with Scaling.')
                print('Rotate take 90 for CW, 180, or -90 for CCW rotations only')
                quit()
            case '-a':
                bAnalyseOnly = True
                print('Analysis Only Mode - no output')
            case '-c':
                bCleanMode = True
            case '-l':
                minOn = float(userData)
                bLaserMode = True
            case '-s':
                defaultScale = (float(userData))
                scale.setXYZ(defaultScale)
            case '-w':
                tarWidth = float(userData)
            case '-d':
                tarDepth = float(userData)
            case '-r':
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
    userIn = input('Laswer PWM off limit ({}):'.format(str(minOn)))
    if userIn != '': minOn = float(userIn) 


if filenameIn == '':
    filenameIn = input('Input filename:')
if filenameOut == '':
    filenameOut = 'out{0}_{1}deg_{2}x_x{3}y{4}'.format(filenameIn,rotation,defaultScale,offset.x,offset.y)
if defaultScale!= 1 and ('tarDepth' in globals() or 'tarWidth' in globals()):
    print('scaling and widith or depth cannot be used together. skipping scaling')
    #skipping happens automatically as fixed width and depth will overwrite any fixed scaler

ProcessFile(filenameIn,filenameOut)
