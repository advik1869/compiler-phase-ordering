# Removing an unused duplicate leaves the live repeated-expression use.
a = 4
b = 5
dead = a + b
t1 = a + b
t2 = a + b
answer = t1 + t2
answer2 = answer + 1
return answer2
