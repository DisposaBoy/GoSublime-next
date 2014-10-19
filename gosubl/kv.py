import threading
import traceback

class P(object):
	def __init__(self, k, v):
		self.k = k
		self.v = v

class L(object):
	def __init__(self):
		self.lck = threading.Lock()
		self.lst = []

	def get(self, k, df=None):
		v, _ = self.gets(k, df=df)
		return v

	def gets(self, k, df=None):
		with self.lck:
			for p in self.lst:
				if p.k == k:
					return (p.v, False)

			if df:
				try:
					x = df()
					if store:
						self.lst.append(P(k, x[1]))

					return x
				except Exception:
					traceback.print_exc()

			return (None, False)

	def put(self, k, v):
		with self.lck:
			for p in self.lst:
				if p.k == k:
					v, p.v = p.v, v
					return v

			self.lst.append(P(k, v))
			return None

	def delete(self, k):
		with self.lck:
			pos = -1
			v = None
			for i, p in enumerate(self.lst):
				if p.k == k:
					pos = i
					v = p.v
					break

			if pos >= 0:
				del self.lst[pos]

			return v

	def sort(self, key=None, reverse=False):
		with self.lck:
			if not key:
				key = lambda p: p.k

			self.lst.sort(key=key, reverse=reverse)

	def keys(self):
		with self.lck:
			return [p.k for p in self.lst]

	def values(self):
		with self.lck:
			return [p.v for p in self.lst]

	def __len__(self):
		with self.lck:
			return len(self.lst)

class M(object):
	def __init__(self):
		self.lck = threading.Lock()
		self.d = {}

	def get(self, k, df=None):
		with self.lck:
			v = self.d.get(k, None)

		if v is None and df is not None:
			try:
				v, store = df()
				if store:
					with self.lck:
						self.d[k] = v
			except Exception:
				v = None
				print(traceback.format_exc())

		return v

	def put(self, k, v):
		with self.lck:
			old_v = self.d.get(k, None)
			self.d[k] = v
			return old_v

	def delete(self, k):
		with self.lck:
			old_v = self.d.get(k, None)

			try:
				del self.d[k]
			except Exception:
				pass

			return old_v

	def incr(self, k, i=1):
		with self.lck:
			old_v = self.d.get(k, 0)
			self.d[k] = old_v + i
			return old_v

	def decr(self, k, i=1):
		with self.lck:
			old_v = self.d.get(k, 0)
			self.d[k] = old_v - i
			return old_v

	def dict(self):
		with self.lck:
			return self.d.copy()

	def keys(self):
		with self.lck:
			return list(self.d.keys())

	def values(self):
		with self.lck:
			return list(self.d.values())

	def clear(self, m={}):
		with self.lck:
			self.d = m

	def filter(self, f, keys=[]):
		with self.lck:
			if not keys:
				keys = list(self.d.keys())

			for k in keys:
				v = f(k, self.d.get(k))
				if v:
					self.d[k] = v
				else:
					try:
						del self.d[k]
					except KeyError:
						pass

	def __len__(self):
		with self.lck:
			return len(self.d)

class O(object):
	def __init__(self, **kw):
		self.__dict__.update(kw)

class Counter(object):
	def __init__(self):
		self.n = 0
		self.lck = threading.Lock()

	def next(self):
		with self.lck:
			self.n += 1
			return self.n

def filter_bool(it):
	return [v for v in it if v]

def filter_none(it):
	return [v for v in it if v is not None]

def id(v):
	return v

def filter_join(it, sep='', out=None):
	if not out:
		out = id
	return sep.join((out(v) for v in it if v))
