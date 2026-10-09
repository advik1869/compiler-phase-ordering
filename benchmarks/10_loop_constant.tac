# A bounded loop repeatedly uses a constant expression.
i = 0
limit = 3
acc = 0
invariant = 2 + 3
loop:
if i >= limit goto done
temp = acc + invariant
acc = temp
i = i + 1
goto loop
done:
return acc
