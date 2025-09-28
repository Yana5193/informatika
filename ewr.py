#1 вариант 1 задача
m=[]
s=0
while True:
    n=int(input())
    s+=n
    m.append(n)
    if s==0:
        break
print(sum(i*i for i in m))

