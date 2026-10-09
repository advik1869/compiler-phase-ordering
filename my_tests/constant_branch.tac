a = 10
b = 20
c = a + b
x = c * 2
y = x + 5
unused = 999

if c > 20 goto L1
z = 100
goto L2

L1:
result = y + 10

L2:
print result
return result