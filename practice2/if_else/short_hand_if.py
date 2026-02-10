a = 10
b = 20

# one-line if
if a < b: print("a is smaller")  # ok for tiny cases

# ternary expression
bigger = "a" if a > b else "b"
print("Bigger is:", bigger)

# another ternary example
age = 17
status = "adult" if age >= 18 else "minor"
print(status)