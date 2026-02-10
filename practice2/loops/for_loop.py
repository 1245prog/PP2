"""
For Loops
Iterate over a sequence (list, string, range, etc.)
"""

# over a list
fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
    print(fruit)

# over a string
for ch in "Python":
    print(ch)

# range(start, stop, step)
for n in range(1, 6):
    print("n =", n) # 1, 2, 3, 4, 5 without 6

for n in range(0, 11, 2): # 0, 2, 4, 6, 8, 10, with step 2
    print("even:", n)