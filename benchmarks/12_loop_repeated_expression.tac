# Repeated expressions occur inside a terminating loop.
i = 0
limit = 3
a = 2
b = 4
acc = 0
loop:
if i >= limit goto done
t1 = a + b
t2 = a + b
acc = acc + t2
i = i + 1
goto loop
done:
return acc
