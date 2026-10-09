# A larger deterministic case combining constants, CSE, dead code, and a branch.
a = 2
b = 3
c = a + b
t1 = c * 2
t2 = c * 2
dead = t1 + 100
if c > 0 goto use
fallback = 0
goto finish
use:
value = t1 + t2
finish:
answer = value + 1
return answer
