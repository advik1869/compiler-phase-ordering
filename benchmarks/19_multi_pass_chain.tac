# Propagation, folding, and dead-code elimination interact in sequence.
a = 7
b = a
c = b + 3
dead = c * 100
d = c * 2
e = d - 1
f = e + 1
g = f - 1
return g
