# An expression remains reusable across unrelated instructions.
a = 6
b = 2
t1 = a * b
x = 10
y = x + 1
t2 = a * b
answer = t1 + t2
answer2 = answer + y
return answer2
