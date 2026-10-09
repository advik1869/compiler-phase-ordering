# Constant propagation through several definitions.
a = 10
b = a
c = b
d = c + 5
e = d * 2
f = e + 1
g = f - 1
return g
