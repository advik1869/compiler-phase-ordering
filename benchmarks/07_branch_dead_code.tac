# Branch-local computations whose values are not observable.
a = 1
if a == 1 goto left
dead_right = a + 20
goto join
left:
dead_left = a + 30
join:
result = 42
return result
