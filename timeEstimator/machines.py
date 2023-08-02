from math import sqrt, pi
from .utils import *
import re

class Biglia():
    """go inside machine.py to configure the lathe to correspond to your lathe's specifications"""
    def __init__(self) -> None:
        self.position = (0,0) # mm x,z
        self.cuttingSpeed = 0 #m/min
        self.feed = 0 #mm/tour
        self.perRevolutionFeed = True #IS SPEED ? mm/min si false
        self.maxSpeed = 12500 #mm/min
        self.rotation = 0 #1/min
        self.maxRotation = 5000#G92
        self.isRotationConstant = False #are we in G97 mode (True) or in G96 (False => we use Vc cuttingSpeed to calculate N - the rotation - to get time)
        self.toolName = ""
        
        self.variables = {}
        
        self.currentCycle = ""
        self.cycleTime = 0 #current cycle accumulated time
        self.deadCycleTime = 0 #not machining (fast interpolations)
        
        self.csvData = {} #to return at the end later on
        self.globalTime = 0.0  #to return for testing purpuses
    
    def move_and_get_time_linear(self, new_pos, fast = False) -> float:
        """moves the tool to its new position in a linear trajectory. returns the necessary time"""
        X = new_pos[0]
        Z = new_pos[1]

        #determine the speed depending on the machinning factors
            
        #=====position setter =======
        if not X :
            X = self.position[0]
        else :
            X = float(X[1:].replace(",",""))
            
        if not Z :
            Z = self.position[1]
        else :
            Z = float(Z[1:].replace(",",""))
            
        #=== speed setter ===
        if not self.perRevolutionFeed :
            speed = self.feed
        elif self.isRotationConstant:
            speed = self.rotation * self.feed
        elif not fast and not self.isRotationConstant:
            D_moyen = X + self.position[0]
            rot_moyen = 1000 * self.cuttingSpeed / (pi * D_moyen)
            if rot_moyen > self.maxRotation : rot_moyen = self.maxRotation
            speed = rot_moyen * self.feed
                
        #=== distance setter ===
            
        dist = sqrt((X-self.position[0])**2 + (Z-self.position[1])**2)
        
        if fast:
            time = dist / self.maxSpeed
        elif not fast:
            time = dist / speed
            
        self.position = (X,Z)
        self.globalTime += time*60
        return time*60 #return seconds
    
    def sendDataAndReset(self) -> None:
        """returns all the current cycle data for logging and reset the cycle time"""
        if (self.cycleTime == 0 and self.deadCycleTime == 0) or len(self.toolName) <= 1:
            return
        #print(self.toolName + " => " + str(self.cycleTime + self.deadCycleTime) + " seconds")
        self.cycleTime = 0
        self.deadCycleTime = 0
        return
    
    def interpret(self, line):
        """get a line, interprets it and stores toolname, op type and time for csv indentation in its (the lathe) inernal dataset"""
        
        line = re.sub("\(.*?\)","",line)
        var = getVar(line)
        if var:
            self.variables[var[0]] = var[1]
        
        #\/ \/ \/ \/ to treat variables : should add a dict "self.varibles" stocking vars id "[]" is detected in a non G line and then self.readVar() is called if a "[]" is detected in a G line\/ \/ \/ \/ 
            
        #=====================
        #   TOOL NAME GETTER 
        #=====================
        
        T = getParam(line, "T")
        
        if T != None:
            self.toolName = T
            #if this is a new tool, we return the tool times and procced to treat the next
            #HERE SHOUL ADD A NEW ENTRY TO THE DATA DICT
            
        #=====================
        #  FEED SPEED GETTER
        #=====================
        
        F = getParam(line, "F")
        
        if F != None and F != "":
            self.feed = float(F[1:])
        
        #=====================
        # G CODES INTERPRETER
        #=====================
        
        #we get the current cycle so we can spread it across lines
        G = getParam(line, "G")
        if G != None and G != self.currentCycle and "G" in G:
            self.currentCycle = G
            
        #and now, we cover all G codes possibilities...
        
        #-----------------------------
        #Cutting speeds G getters
        #-----------------------------
        
        #look for G95 or G94 to determine thje state of self.perRevoltionFeed (true id mm/tr and false if mm/min)
        if "G95" in line or "G99" in line:
            self.perRevolutionFeed = True
        if "G94" in line or "G98" in line:
            self.perRevolutionFeed = False
        
        #G97 says we use constant rotation speed, thus using cuuting speed useless
        if "G97" in line:
            #Definition de vitesse de rotation constante
            S = getParam(line, "S")
            if S:
                self.isRotationConstant = True
                self.rotation = float(S[1:])
                
        #G92 here, maximum rotation speed rate
        if "G92" in line:
            S = getParam(line, "S")
            if S:
                self.maxRotation = float(S[1:])
                
        #G96 tells us we use cutting speed to move the  tool
        if "G96" in line:
            S = getParam(line, "S")
            if S:
                self.isRotationConstant = False
                self.cuttingSpeed = float(S[1:])
        
        #-----------------------------
        #Machinning cycles G getters
        #-----------------------------
        
        X = getParam(line, "X", self.variables)
        Z = getParam(line, "Z", self.variables)
        U = getParam(line, "U", self.variables)
        W = getParam(line, "W", self.variables)
        
        #a little dirty but who cares really ? it was a quick fix. maybe do it a little better and rework the "param getting" when i have the time
        if not X and U:
            X = "X" + str(self.position[0] + float(U[1:]))
        if not Z and W:
            Z = "Z" + str(self.position[1] + float(W[1:]))
        
        #G0 : fast linear interpolation
        if self.currentCycle in ["G00", "G0"]:
            self.deadCycleTime += self.move_and_get_time_linear((X,Z), fast = True) #add the cycle time to the current time cycle
            
        #G01 : linear mouvement
        if self.currentCycle in ["G01", "G1"]:
            self.cycleTime += self.move_and_get_time_linear((X,Z), fast = False) #add the cycle time to the current time cycle

        
        #G2 and G3 to add in the end