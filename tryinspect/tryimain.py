import tryi

class A:
  def a(self):
    print("A.a()")
    B().b()

class B:
  def b(self):
    print("B.b()")
    tryi.f()

def c():
    tryi.f()

A().a()
c()
tryi.f()