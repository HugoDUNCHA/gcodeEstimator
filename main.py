from machine import Lathe

lathe = Lathe()

filename = "G.txt"

with open(filename, "r") as file:
    for line in file:
        #get data from the line to insert into a csv file
        data = lathe.interpret(line)