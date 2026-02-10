"""
- and, or, not
and | True and True = True -> if all statment are True the result will be True
or  | True or False = True -> if at least one statment is True the result will be True
not | not(True) = False, not(False) = True
"""

x = 5

print(x > 3 and x < 10)   # True
print(x > 3 and x < 4)    # False

print(x < 3 or x < 10)    # True
print(x < 3 or x > 10)    # False

print(not (x < 10))       # False  

# Precedence demo
print(True or False and False)   # True ('and' runs first => True or (False) => True)
print((True or False) and False) # False