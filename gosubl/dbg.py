import pprint
import time

pp = pprint.PrettyPrinter()

class Repr(object):
	def __repr__(self):
		return s(dict((k,v) for k,v in self.__dict__.items() if not k.startswith('_')))

def p(*a):
	l = [time.strftime('%H:%M:%S')]
	l.extend(a)
	pp.pprint(l)

def s(*a):
	if len(a) == 1:
		a = a[0]

	return pp.pformat(a)
