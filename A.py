class yo:
    def b(self):
        print('b')
    def a(self):
        print('a')
    def test(self,v):
        handler = getattr(self, v, None)
        if handler:
            handler()
        else:
            pass
a=yo()
a.test('f')

