# Constants, a dead value, and a repeated expression in one straight-line program.
a = 4
b = 6
c = a + b
dead = c * 100
t1 = c * 2
t2 = c * 2
u = t1 + t2
v = u - a
return v
