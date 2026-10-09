# Repeated additions provide a simple CSE opportunity.
a = 7
b = 3
t1 = a + b
t2 = a + b
t3 = t2 + t1
t4 = t3 + b
t5 = t4 - a
t6 = t5 + 1
return t6
