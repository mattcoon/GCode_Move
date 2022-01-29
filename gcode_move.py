# gcode_move by Matthew Coon
# written to support easy manipulation of GCODE for 3d printing or laser cutting
# - moving offset to object from 0,0,0
# - scaling feed, extrusion, or X,Y,Z
# - analysis only mode with statistics before and after modification
# - runs command line or interactive
# - rotates image by 90 or 180 deg
# TODO: enable individual interactive for missing components of commandline
# TODO: add axis rotation
# TODO: get __add__ __sub__ working for axis

from pathlib import Path
import re
import sys

class axis:
    def __init__(self,x=0,y=0,z=0,f=0,e=0) -> None:
        self.x = x
        self.y = y 
        self.z = z
        self.f = f
        self.e = e
    def __add__(self,addr):
        return axis(self.x+addr.x, self.y+addr.y, self.z+addr.z, self.f+addr.f, self.e+addr.e)
    def __sub__(self,addr):
        return axis(self.x-addr.x, self.y-addr.y, self.z-addr.z, self.f-addr.f, self.e-addr.e)
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
    global scaleXYZ
    global axis
  
    bLaserOn=False
    bScaledXYZ=False
    delta = offset

    initialMin = axis()
    initialMin.copy(LimMax)
    initialMax = axis()
    finalMin = axis()
    finalMin.copy(LimMax)
    finalMax = axis()

    if scaleXYZ != 1:
        bScaledXYZ = True
    if not bAnalyseOnly:
        fileOut = open(Path(filenameOut),'w')
        print("Writing to "+filenameOut)

    with open(Path(filenameIn),'r') as fileIn:
        # Find offset with finMinX and MinY
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
            # TODO: delta = delta - initialMin should work
            delta.x -= initialMin.x
            delta.y -= initialMin.y
            delta.z -= initialMin.z
        if 'tarDepth' in globals():
            scaleXYZ = tarDepth/(initialMax.y-initialMin.y)
            bScaledXYZ = True
        if 'tarWidth' in globals():
            scaleXYZ = tarWidth/(initialMax.x-initialMin.x)
            bScaledXYZ = True

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
                                #leave G0/G1 alone a pass thru
                                lineNew = parts
                        else:
                            valuestr = findFloat(parts,parts[0:1])
                            if valuestr:
                                currentPos = float(valuestr.groups()[0])
                            else:
                                currentPos = 0
                            match parts[0:1]:
                                case 'X':
                                    if bScaledXYZ:
                                        currentPos = Scale(currentPos-initialMin.x,scaleXYZ,0,LimMax.x)+initialMin.x
                                    currentPos = Transpose(currentPos,delta.x,0,LimMax.x)
                                    lineNew+= ' {0:s}{1:.6f}'.format(parts[0:1],currentPos)
                                    finalMax.x = max(currentPos,finalMax.x)
                                    finalMin.x = min(currentPos,finalMin.x)
                                case 'Y':
                                    if bScaledXYZ:
                                        currentPos = Scale(currentPos-initialMin.y,scaleXYZ,0,LimMax.y)+initialMin.y
                                    currentPos = Transpose(currentPos,delta.y,0,LimMax.y)
                                    lineNew+= ' {0:s}{1:.6f}'.format(parts[0:1],currentPos)
                                    finalMax.y = max(currentPos,finalMax.y)
                                    finalMin.y = min(currentPos,finalMin.y)
                                case 'Z':
                                    if bScaledXYZ:
                                        currentPos = Scale(currentPos-initialMin.z,scaleXYZ,0,LimMax.z)+initialMin.z
                                    currentPos = Transpose(currentPos,delta.z,0,LimMax.z)
                                    lineNew+= ' {0:s}{1:.6f}'.format(parts[0:1],currentPos)
                                    finalMax.z = max(currentPos,finalMax.z)
                                    finalMin.z = min(currentPos,finalMin.z)
                                case 'F':
                                    currentPos = Scale(currentPos,scale.f,0,LimMax.f)
                                    lineNew+= ' '+parts[0:1]+str(currentPos)
                                case 'E':
                                    currentPos = Scale(currentPos,scale.e,-LimMax.e,LimMax.e)
                                    lineNew+= ' '+parts[0:1]+str(currentPos)
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
                #check for laser off
                if linesplit[0] == "M107":
                    bLaserOn = False
                if bAnalyseOnly == False:
                    fileOut.write(line)
        finalMin.min(finalMax)
        print('Scaled by '+'{:.2f}'.format(scaleXYZ)+'.')
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
    
offset = axis(0,0,0)
scale = axis(1,1,1,1,1)
scaleXYZ = 1.0
LimMax = axis (220, 220,250,50000,50000)
LimMin = axis (0, 0, 0)
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
                print('           -aAnalyseOnly -lLaserlowerLimit -sScaleXYZ -cClean -wWidth -dDepth -rRotate')
                print('Feedrates are in percent. Offset in mm.')
                print('laser affects fanspeed 0-255 before turning off laser and puts in laser mode. ')
                print('G1 while laser is off will become G0. use -l0 to keep laser PWMs but use G1/G0 substitutions')
                print('XYZ scaling will treat as a mulitpler for any present components while keeping offsets. Note for 3d')
                print('the first line is in scope and will prevent use of offset for scaling')
                print('Clean mode removes all offsets and sets object to 0 offset.')
                print('If cleanmode and offset used, will set object to absolute locations')
                print('Width and Depth cannot be used together or with Scaling.')
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
                scaleXYZ = float(userData)
            case '-w':
                tarWidth = float(userData)
            case '-d':
                tarDepth = float(userData)
            case 'r':
                if userData == 90:
                    rotate = 90
                elif userData == -90:
                    rotate = -90
                elif userData == 180:
                    rotate = 180
                else:
                    print('Rotation of {:0} not allowed.'.format(userData))
else:
    print('no args - defaults in ( )')
    userIn = input('X Offset ({:}):'.format(str(offset.x)))
    if userIn != '': offset.x = float(userIn) 
    userIn = input('Y Offset ({:}):'.format(str(offset.y)))
    if userIn != '': offset.y = float(userIn) 
    userIn = input('Z Offset ({:}):'.format(str(offset.z)))
    if userIn != '': offset.z = float(userIn) 
    userIn = input('XYZ Scaling ({:}):'.format(str(scaleXYZ)))
    if userIn != '': scaleXYZ = float(userIn) 
    userIn = input('Feed Rate scaling ({:}):'.format(str(scale.f)))
    if userIn != '': scale.f = float(userIn) 
    userIn = input('Extruder Rate scaling ({:}):'.format(str(scale.e)))
    if userIn != '': scale.e = float(userIn) 
    userIn = input('Max X value ({:}):'.format(str(LimMax.x)))
    if userIn != '': LimMax.x = float(userIn) 
    userIn = input('Max Y value ({:}):'.format(str(LimMax.y)))
    if userIn != '': LimMax.y = float(userIn) 
    userIn = input('Max Z value ({:}):'.format(str(LimMax.z)))
    if userIn != '': LimMax.z = float(userIn) 
    userIn = input('Max feedrate ({:}):'.format(str(LimMax.f)))
    if userIn != '': LimMax.f = float(userIn) 
    userIn = input('Max Extruder ({:}):'.format(str(LimMax.e)))
    if userIn != '': LimMax.e = float(userIn) 
    userIn = input('Laswer PWM off limit ({:}):'.format(str(minOn)))
    if userIn != '': minOn = float(userIn) 
    filenameIn = input('Input filename:')


if filenameOut == '':
    filenameOut = 'out'+filenameIn
if 'tarDepth' in globals() and 'tarWidth' in globals():
    print('fixed width and depth cannot be both set')
    quit()
if scaleXYZ != 1 and ('tarDepth' in globals() or 'tarWidth' in globals()):
    print('scaling and widith or depth cannot be used together. skipping scaling')

ProcessFile(filenameIn,filenameOut)




