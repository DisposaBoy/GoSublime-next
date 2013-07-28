import copy
import threading
import traceback

class M(object):
	def __init__():
		self.lck = threading.Lock()
		self.d = {}

	def _get(k, df):
		# not passing d as default because the stored value can, itself, be `None`
		v = self.d.get(k, None)

		if v is None and df is not None:
			try:
				v, store = df()
				if store:
					self.d[k] = v
			except Exception:
				v = None
				print(traceback.format_exc())

		return v

	def get(k, df=None):
		with self.lck:
			return copy.copy(self._get(k, df))

	def ref(k, df=None):
		with self.lck:
			return self._get(k, df)

	def put(k, v):
		with self.lck:
			old_v = self._get(k, None)
			self.d[k] = v
			return old_v

	def delete(k):
		with self.lck:
			old_v = self._get(k, None)

			try:
				del self.d[k]
			except Exception:
				pass

			return old_v

	def _df_zero(self):
		return (0, False)

	def incr(k, i=1):
		with self.lck:
			old_v = self._get(k, self._df_zero)
			self.d[k] = old_v + i
			return old_v

	def decr(k, i=1):
		with self.lck:
			old_v = self._get(k, self._df_zero)
			self.d[k] = old_v - i
			return old_v
