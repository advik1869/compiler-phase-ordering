# Branches combine a constant condition, useful values, and dead values.
a = 8
b = 2
if a > b goto high
dead_low = a + b
value = b * 3
goto finish
high:
shared = a - b
dead_high = shared * 9
value = shared + shared
finish:
answer = value + 1
return answer
