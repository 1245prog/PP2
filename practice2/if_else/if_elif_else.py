"""
If Elif Else
Multiple conditions, first match wins.
"""

score = 82

if score >= 90: # False
    print("A")
elif score >= 80: # True
    print("B")
elif score >= 70: # we have not reached this condition
    print("C")
else:
    print("D or below") # Execute if none of the conditions are True

# Tip: order matters!