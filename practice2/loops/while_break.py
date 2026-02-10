"""
While Loop Break
break stops the loop immediately.
"""

i = 1
while i <= 10:
    if i == 6:
        print("Stopping early at", i)
        break # break loop if the condition is true
    print(i)
    i += 1