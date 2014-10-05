from . import kv
import datetime
import string
import sublime
import threading
import time
import traceback

DOMAIN = 'GoSublime.ui'
ORD_BASE = -50
ORD_TASK = ORD_BASE + 1
ORD_ERROR = ORD_BASE + 2
ORD_NOTE = ORD_BASE + 3
TIMEOUT = datetime.timedelta(seconds=10)
TIMEOUT_ZERO = datetime.timedelta()
TIMEOUT_BUSY_WAIT = datetime.timedelta(seconds=1)
TIMEOUT_ERROR = datetime.timedelta(seconds=20)
MDASH = u'\u2014'
status_sep = ' '+MDASH+' '
BULLET = u'\u2022'
now = datetime.datetime.now

class StatusMgr(threading.Thread):
	def __init__(self):
		super(StatusMgr, self).__init__()
		self.pos = 0
		self.dt = now()
		self.lck = threading.Lock()
		self.dl = []
		self.text = ''

	def drawer(self, key, order=0):
		with self.lck:
			for d in self.dl:
				if d.key == key:
					return d

			d = Drawer(self, key=key, order=order)
			self._link(d)
			return d

	def _link(self, d):
		self.dl.append(d)
		self.dl.sort(key=lambda d: d.order)

	def link(self, d):
		with self.lck:
			self._link(d)

	def drawers(self):
		with self.lck:
			return self.dl.copy()

	def end(self, d):
		with self.lck:
			try_remove(self.dl, d)

	def tick(self):
		time.sleep(0.250)
		self.dt = now()
		pos = (int(self.dt.microsecond / 250000) + 1) % 4
		if self.pos != pos:
			self.pos = pos
			self.draw()

	def draw(self):
		with self.lck:
			drawers = self.dl.copy()

		tl = []
		for d in drawers:
			t = try_draw(self, d)
			if t:
				tl.append(t)

		text = status_sep.join(tl)
		if self.text != text:
			self.text = text
			sublime.set_timeout(self.refresh, 0)

	def refresh(self, view=None):
		k = 'GoSublime.ui.status'
		text = self.text

		if view is None:
			try:
				view = sublime.active_window().active_view()
			except Exception:
				return

		if view is not None:
			view.set_status(k, text)

	def run(self):
		while True:
			self.tick()

class Drawer(object):
	def __init__(self, mgr, text='', key='', order=0, timeout=None):
		self.mgr = mgr
		self.key = key
		self.order = order
		self.timeout = timeout
		self.set_text(text)

	def ready(self, dt):
		return True

	def expired(self, dt):
		if self.timeout is None:
			return False

		if not self.timeout:
			return True

		return dt - self.dt >= self.timeout

	def set_timeout(self, timeout):
		self.timeout = timeout

	def set_text(self, text):
		self.text = str(text)
		self.dt = now()

	def draw(self, st):
		return self.text

	def end(self):
		self.mgr.end(self)

class TaskDrawer(Drawer):
	def __init__(self, mgr, text='', key='', cancel=None, timeout=TIMEOUT):
		super(TaskDrawer, self).__init__(mgr, text=text, key=key, timeout=timeout)
		self.cancel = cancel
		self.started = self.dt

class TaskMgr(Drawer):
	def __init__(self, mgr, order=0):
		super(TaskMgr, self).__init__(mgr, order=order)
		self.dl = []
		self.lck = threading.Lock()
		self.n = 0

	def end(self, d):
		with self.lck:
			try_remove(self.dl, d)

	def task(self, key):
		if not key:
			return None

		with self.lck:
			for d in self.dl:
				if d.key == key:
					return d

		return None

	def cancel(self, key):
		d = self.task(key)
		if not d or not d.cancel:
			return False

		if sublime.ok_cancel_dialog('Are you sure you want to cancel` task #%s?\n\n%s' % (d.key, d.text)):
			d.cancel()

		return True

	def begin(self, text, cancel=None, timeout=TIMEOUT):
		with self.lck:
			self.n += 1
			d = TaskDrawer(self, text=text, key=str(self.n), cancel=cancel, timeout=timeout)
			self.dl.append(d)

		return d

	def drawers(self):
		with self.lck:
			return self.dl.copy()

	def draw(self, st):
		if not self.dl:
			return ''

		n = 0
		s = ''
		dt = None
		with self.lck:
			for d in self.dl:
				if st.dt - d.dt < TIMEOUT_BUSY_WAIT:
					continue

				n += 1
				if dt is None or d.dt >= dt:
					dt = d.dt
					s = try_draw(st, d)

		if n == 0:
			return ''

		b = BULLET * n
		frames = (b+'  ', ' '+b+' ', '  '+b, ' '+b+' ')
		return frames[st.pos] + (' ' + s if s else s)

def try_remove(dl, d):
	try:
		dl.remove(d)
	except ValueError:
		pass

def try_draw(st, d):
	if d.expired(st.dt):
		return ''

	try:
		return d.draw(st)
	except Exception:
		trace(DOMAIN)
		return ''

def gs_init(m={}):
	pass

def task(domain, text, cancel=None, set_status=True):
	timeout = TIMEOUT if set_status else TIMEOUT_ZERO
	return taskd.begin(text, cancel=cancel, timeout=timeout)

def error(domain, text):
	print('GoSublime error @ %s: %s: %s' % (now(), domain, text))
	errord.set_text('Error: ' + text.split('\n')[0])

def trace(domain, text=''):
	try:
		tb = traceback.format_exc().strip()
	except Exception:
		tb = ''

	if not text:
		i = tb.rfind('\n')
		if i > 0:
			text = tb[i:].strip() + '\n' + text

	text += '\n' + tb
	error(domain, text.strip())

def note(domain, text):
	noted.set_text(text)

def task_ents():
	ents = []
	dt = now()
	m = {}
	dl = taskd.drawers()
	if dl:
		dl.sort(key=lambda d: d.dt, reverse=True)
		for i, d in enumerate(dl, start=1):
			pfx = 'Cancel task' if d.cancel else 'Task'
			m[len(ents)] = d.key
			ents.append([
				'%d/%d, %s #%s' % (i, len(dl), pfx, d.key),
				d.text,
				'started: %s' % d.started,
				'elapsed: %s' % (dt - d.started),
			])
	else:
		ents = [['', 'There are no active tasks']]

	return (ents, lambda i, _: taskd.cancel(m.get(i, '')))

status = StatusMgr()

taskd = TaskMgr(status, order=ORD_TASK)
status.link(taskd)

errord = Drawer(status, order=ORD_ERROR, timeout=TIMEOUT_ERROR)
status.link(errord)

noted = Drawer(status, order=ORD_NOTE, timeout=TIMEOUT)
status.link(noted)

status.start()
