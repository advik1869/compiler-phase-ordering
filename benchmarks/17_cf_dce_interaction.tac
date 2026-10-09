# Foldable computations form a dead chain beside the observable result.
a = 2
b = 3
dead1 = a + b
dead2 = dead1 * 4
dead3 = dead2 - 1
dead4 = dead3 + 8
dead5 = dead4 * 2
answer = a + b
return answer
