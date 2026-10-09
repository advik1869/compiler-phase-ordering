# The same expression is computed on both sides of a control-flow join.
a = 4
b = 5
if a < b goto left
t = a + b
goto join
left:
t = a + b
join:
result = t * 2
return result
