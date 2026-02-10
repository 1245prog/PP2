"""
For Loop Break
break exits the loop.
"""

for n in range(1, 11):
    if n == 5:
        print("Found 5, breaking.")
        break
    print(n)