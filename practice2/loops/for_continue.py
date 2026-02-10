"""
For Loop Continue
continue skips to the next iteration.
"""

for n in range(1, 11):
    if n % 3 == 0:
        continue  # skip multiples of 3
    print(n)