# Redefining an operand must invalidate the earlier expression.
a = 2
b = 3
t1 = a + b
a = 10
t2 = a + b
t3 = t2 * 2
t4 = t3 + 1
return t4
