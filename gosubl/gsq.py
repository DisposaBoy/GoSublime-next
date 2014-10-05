from . import gs
from . import ui
import sublime
import threading

DOMAIN = 'GsQ'

class Launcher(threading.Thread):
	def __init__(self, domain, f):
		threading.Thread.__init__(self)
		self.daemon = True
		self.domain = domain
		self.f = f

	def run(self):
		try:
			self.f()
		except Exception:
			gs.trace(self.domain)

class Runner(threading.Thread):
	def __init__(self, domain, f, msg='', set_status=False, cancel=None):
		threading.Thread.__init__(self)
		self.daemon = True
		self.domain = domain
		self.f = f
		self.msg = msg
		self.set_status = set_status
		self.cancel = cancel

	def run(self):
		t = ui.task(self.domain, self.msg, cancel=self.cancel, set_status=self.set_status)
		try:
			self.f()
		except Exception:
			ui.trace(self.domain)
		finally:
			t.end()

class GsQ(threading.Thread):
	def __init__(self, domain):
		threading.Thread.__init__(self)
		self.daemon = True
		self.q = gs.queue.Queue()
		self.domain = domain

	def run(self):
		while True:
			try:
				t = ui.task(self.domain, msg, set_status=set_status)
				try:
					f()
				except Exception:
					ui.trace(self.domain)
				finally:
					t.end()
			except:
				pass


	def dispatch(self, f, msg, set_status=False):
		try:
			self.q.put((f, msg, set_status))
		except Exception:
			gs.trace(self.domain)

try:
	m
except:
	m = {}

def dispatch(domain, f, msg='', set_status=False):
	global m

	q = m.get(domain, None)
	if not (q and q.is_alive()):
		q = GsQ(domain)
		q.start()
		m[domain] = q

	q.dispatch(f, msg, set_status)

def do(domain, f, msg='', set_status=False, cancel=None):
	Runner(domain, f, msg, set_status, cancel).start()

def launch(domain, f):
	Launcher(domain, f).start()
