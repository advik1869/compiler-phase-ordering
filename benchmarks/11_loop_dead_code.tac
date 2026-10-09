# A dead temporary is computed on every loop iteration.
i = 0
limit = 3
result = 7
loop:
if i >= limit goto done
dead = i + 100
i = i + 1
goto loop
done:
return result
