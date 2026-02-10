"""
While Loop Continue
continue skips the rest of the current iteration.
"""

i = 0
while i < 10:
    i += 1
    if i % 2 == 0:
        continue  # skip evens if condition is true
    print("Odd:", i)