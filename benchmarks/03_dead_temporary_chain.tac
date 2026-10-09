# A chain of computations does not contribute to the returned value.
a = 10
b = a + 5
c = b * 2
d = c - 7
e = d + 1
f = e * 2
g = f - 3
return 100
