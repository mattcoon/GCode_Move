# gcode_move by Matthew Coon
# written to support easy manipulation of GCODE for 3d printing or laser cutting
# - moving offset to object from 0,0,0
# - scaling feed, extrusion, or X,Y,Z
# - analysis only mode with statistics before and after modification
# - runs command line or interactive
# TODO: scale based on end size width or height
# TODO: sanity check for -c clean to not conflict with offsets and throw error
# TODO: enable individual interactive for missing components of commandline

from pathlib import Path
import re
import sys


def findFloat (str,param):
    reSearch = re.compile(param+'(\d*.\d*)')
    parts = reSearch.search(str)
    return parts

def findInt (str,param):
    reSearch = re.compile(param+'(\d*)')
    parts = reSearch.search(str)
    return parts


def ProcessFile (filenameIn, filenameOut):
    
    bLaserOn=False
    bScaledXYZ=False
    deltaX = offsetX
    deltaY = offsetY
    deltaZ = offsetZ

    finMinX  = LimMaxX
    initMinX = finMinX
    finMaxX  = 0.0
    initMaxX = finMaxX
    
    finMinY  = LimMaxY
    initMinY = finMinY
    finMaxY  = 0.0
    initMaxY = finMaxY
    
    finMinZ  = LimMaxZ
    initMinZ = finMinZ
    finMaxZ  = 0.0
    initMaxZ = finMaxZ

    if scaleXYZ != 1:
        bScaledXYZ = True
    if bAnalyseOnly == False:
        fileOut = open(Path(filenameOut),'w')
        print("Writing to "+filenameOut)

    with open(Path(filenameIn),'r') as fileIn:
        # Find offset wiht finMinX and MinY
        for line in fileIn:
            if line[0:1] == 'G':
                for axis in ['X','Y','Z']:
                    axisValue = findFloat(line,axis)
                    if axisValue:
                        position = float(axisValue.groups()[0])
                        match axis:
                            case 'X':
                                initMinX = min(initMinX,position)
                                initMaxX = max(initMaxX,position)
                            case 'Y':
                                initMinY = min(initMinY,position)
                                initMaxY = max(initMaxY,position)
                            case 'Z':
                                initMinZ = min(initMinZ,position)
                                initMaxZ = max(initMaxZ,position)
        
        # if no positions found in axis, min will be max, reset that
        initMinX = min(initMinX,initMaxX)
        initMinY = min(initMinY,initMaxY)
        initMinZ = min(initMinZ,initMaxZ)
        if bCleanMode:
            deltaX = -initMinX
            deltaY = -initMinY
            deltaZ = -initMinZ
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
                                        currentPos = Scale(currentPos-initMinX,scaleXYZ,0,LimMaxX)+initMinX
                                    currentPos = Transpose(currentPos,deltaX,0,LimMaxX)
                                    lineNew+= ' {0:s}{1:.6f}'.format(parts[0:1],currentPos)
                                    finMaxX = max(currentPos,finMaxX)
                                    finMinX = min(currentPos,finMinX)
                                case 'Y':
                                    if bScaledXYZ:
                                        currentPos = Scale(currentPos-initMinY,scaleXYZ,0,LimMaxY)+initMinY
                                    currentPos = Transpose(currentPos,deltaY,0,LimMaxY)
                                    lineNew+= ' {0:s}{1:.6f}'.format(parts[0:1],currentPos)
                                    finMaxY = max(currentPos,finMaxY)
                                    finMinY = min(currentPos,finMinY)
                                case 'Z':
                                    if bScaledXYZ:
                                        currentPos = Scale(currentPos-initMinZ,scaleXYZ,0,LimMaxZ)+initMinZ
                                    currentPos = Transpose(currentPos,deltaZ,0,LimMaxZ)
                                    lineNew+= ' {0:s}{1:.6f}'.format(parts[0:1],currentPos)
                                    finMaxZ = max(currentPos,finMaxZ)
                                    finMinZ = min(currentPos,finMinZ)
                                case 'F':
                                    currentPos = Scale(currentPos,scaleF,0,LimMaxF)
                                    lineNew+= ' '+parts[0:1]+str(currentPos)
                                case 'E':
                                    currentPos = Scale(currentPos,scaleE,-LimMaxE,LimMaxE)
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
        finMinX = min(finMinX,finMaxX)
        finMinY = min(finMinY,finMaxY)
        finMinZ = min(finMinZ,finMaxZ)
        print('Scaled by '+'{:.2f}'.format(scaleXYZ)+'.')
        print('Initial')
        print('Min X: {0:.2f} Max X: {1:.2f} width: {2:.2f}'.format(initMinX, initMaxX, initMaxX-initMinX))
        print('Min Y: {0:.2f} Max Y: {1:.2f} width: {2:.2f}'.format(initMinY, initMaxY, initMaxY-initMinY))
        print('Min Z: {0:.2f} Max Z: {1:.2f} width: {2:.2f}'.format(initMinZ, initMaxZ, initMaxZ-initMinZ))
        print('Final')
        print('Min X: {0:.2f} Max X: {1:.2f} width: {2:.2f}'.format(finMinX, finMaxX, finMaxX-finMinX))
        print('Min Y: {0:.2f} Max Y: {1:.2f} width: {2:.2f}'.format(finMinY, finMaxY, finMaxY-finMinY))
        print('Min Z: {0:.2f} Max Z: {1:.2f} width: {2:.2f}'.format(finMinZ, finMaxZ, finMaxZ-finMinZ))



def Transpose (position,offset,limLow,limHi):
    return round(max(limLow,min(limHi,position+offset)),6)

def Scale (position,scale,limLow,LimHi):
    return round(max(limLow,min(LimHi,position*scale)),6)
    

offsetX = 0.0
offsetY = 0.0
offsetZ = 0.0
scaleXYZ = 1.0
scaleF = 1.0
scaleE = 1.0
LimMaxX = 220
LimMaxY = 220
LimMaxZ = 250
LimMaxF = 50000.0
LimMaxE = 50000.0
minOn = 0.0
filenameIn = ''
filenameOut = ''
bAnalyseOnly = False
bCleanMode = False
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
                offsetX = float(userData)
            case '-Y':
                offsetY = float(userData)
            case '-Z':
                offsetZ = float(userData)
            case '-F':
                deltaF = float(userData)
            case '-E':
                deltaE = float(userData)
            case '-h':
                print('gcode_move -iInputFile -oOutputFile -Xoffset -Yoffset -Zoffset -FFeedrate -EExtruderrate')
                print('           -aAnalyseOnly -lLaserlowerLimit -sScaleXYZ -cClean')
                print('Feedrate are in percent. Offset in mm.')
                print('laser affects fanspeed 0-255 before turning off laser and puts in laser mode. ')
                print('G1 while laser is off will become G0. use -l0 to keep laser PWMs but use G1/G0 substitutions')
                print('XYZ scaling will treat as a mulitpler for any present components while keeping offsets. Note for 3d')
                print('the first line is in scope and will prevent use of offset for scaling')
                print('Clean mode removes all offsets and sets object to lowest possible point.')
                quit()
            case '-a':
                bAnalyseOnly = True
            case '-c':
                bCleanMode = True
            case '-l':
                minOn = float(userData)
                bLaserMode = True
            case '-s':
                scaleXYZ = float(userData)
else:
    print('no args - defaults in ( )')
    userIn = input('X Offset ({:}):'.format(str(offsetX)))
    if userIn != '': deltaX = float(userIn) 
    userIn = input('Y Offset ({:}):'.format(str(offsetY)))
    if userIn != '': deltaY = float(userIn) 
    userIn = input('Z Offset ({:}):'.format(str(offsetZ)))
    if userIn != '': deltaZ = float(userIn) 
    userIn = input('XYZ Scaling ({:}):'.format(str(scaleXYZ)))
    if userIn != '': scaleXYZ = float(userIn) 
    userIn = input('Feed Rate scaling ({:}):'.format(str(scaleF)))
    if userIn != '': scaleF = float(userIn) 
    userIn = input('Extruder Rate scaling ({:}):'.format(str(scaleE)))
    if userIn != '': scaleE = float(userIn) 
    userIn = input('Max X value ({:}):'.format(str(LimMaxX)))
    if userIn != '': LimMaxX = float(userIn) 
    userIn = input('Max Y value ({:}):'.format(str(LimMaxY)))
    if userIn != '': LimMaxY = float(userIn) 
    userIn = input('Max Z value ({:}):'.format(str(LimMaxZ)))
    if userIn != '': LimMaxZ = float(userIn) 
    userIn = input('Max feedrate ({:}):'.format(str(LimMaxF)))
    if userIn != '': LimMaxF = float(userIn) 
    userIn = input('Max Extruder ({:}):'.format(str(LimMaxE)))
    if userIn != '': LimMaxE = float(userIn) 
    userIn = input('Laswer PWM off limit ({:}):'.format(str(minOn)))
    if userIn != '': minOn = float(userIn) 
    filenameIn = input('Input filename:')


if filenameOut == '':
    filenameOut = 'out'+filenameIn


ProcessFile(filenameIn,filenameOut)




