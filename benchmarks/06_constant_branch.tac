# The condition is constant, but branch simplification is not assumed.
a = 4
b = 6
c = a + b
if c > 0 goto positive
x = 99
goto done
positive:
x = c * 2
done:
return x
