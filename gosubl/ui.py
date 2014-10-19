from . import kv
import datetime
import string
import sublime
import threading
import time
import traceback

DOMAIN = 'GoSublime.ui'
KEY_TASK = 'gs.00.task'
KEY_ERROR = 'gs.01.error'
KEY_NOTE = 'gs.02.note'
TIMEOUT = datetime.timedelta(seconds=10)
TIMEOUT_ZERO = datetime.timedelta()
TIMEOUT_TASK_NEW = datetime.timedelta(seconds=1)
TIMEOUT_TASK_OLD = datetime.timedelta(seconds=30)
TIMEOUT_ERROR = datetime.timedelta(seconds=20)
MIDDOT = u'\u00B7'
MDASH = u'\u2014'
FRAME_PADDING = ((MIDDOT*1, MIDDOT*3), (MIDDOT*2, MIDDOT*2), (MIDDOT*3, MIDDOT*1), (MIDDOT*2, MIDDOT*2))
status_sep = ' '+MDASH+' '
BULLET = u'\u2022'
now = datetime.datetime.now

class StatusMgr(threading.Thread):
	def __init__(self):
		super(StatusMgr, self).__init__()
		self.pos = 0
		self.dt = now()
		self.dl = kv.L()
		self.text = ''

	def drawer(self, key):
		d, updated = self.dl.gets(key, df=lambda: (Drawer(self, key=key), True))
		if updated:
			self.dl.sort()

		return d

	def link(self, d):
		self.dl.put(d.key, d)
		self.dl.sort()

	def drawers(self):
		return self.dl.values()

	def end(self, d):
		self.dl.delete(d.key)

	def tick(self):
		time.sleep(0.250)
		self.dt = now()
		pos = (int(self.dt.microsecond / 250000) + 1) % 4
		if self.pos != pos:
			self.pos = pos
			self.draw()

	def draw(self):
		tl = []
		for d in self.drawers():
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
	def __init__(self, mgr, text='', key='', timeout=None):
		self.mgr = mgr
		self.key = key
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
	def __init__(self, mgr, key, text='', cancel=None, timeout=TIMEOUT):
		super(TaskDrawer, self).__init__(mgr, text=text, key=key, timeout=timeout)
		self.cancel = cancel
		self.started = self.dt

class TaskMgr(Drawer):
	def __init__(self, mgr, key=''):
		super(TaskMgr, self).__init__(mgr, key=key)
		self.dl = kv.L()

	def end(self, d):
		self.dl.delete(d.key)

	def task(self, key):
		if key:
			return self.dl.get(key)

		return None

	def cancel(self, key):
		d = self.task(key)
		if not d or not d.cancel:
			return False

		if sublime.ok_cancel_dialog('Are you sure you want to cancel task: %s?\n\n%s' % (d.key, d.text)):
			d.cancel()

		return True

	def begin(self, key, text='', cancel=None, set_status=True):
		timeout = TIMEOUT if set_status else TIMEOUT_ZERO
		d = TaskDrawer(self, text=text, key=key, cancel=cancel, timeout=timeout)
		self.dl.put(key, d)
		return d

	def drawers(self):
		return self.dl.values()

	def draw(self, st):
		if not self.dl:
			return ''

		static = 0
		active = 0
		text = ''
		dt = None
		for d in self.drawers():
			age = st.dt - d.dt
			if age < TIMEOUT_TASK_NEW:
				continue

			if age < TIMEOUT_TASK_OLD:
				active += 1
			else:
				static += 1

			if dt is None or d.dt >= dt:
				dt = d.dt
				text = try_draw(st, d)

		if static + active == 0:
			return ''

		static = BULLET * static
		active = BULLET * active
		if active:
			p = FRAME_PADDING[st.pos]
			active = p[0] + active + p[1]

		return ' '.join((s for s in (static, active, text) if s))

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

task_cnt = kv.Counter()
def task(domain, text, cancel=None, set_status=True):
	return taskd.begin(key='#%d' % task_cnt.next(), text=text, cancel=cancel, set_status=set_status)

def error(domain, text):
	print('GoSublime error @ %s: %s: %s' % (now(), domain, text))
	errord.set_text('Error: ' + text.split('\n')[0])

def trace(domain, text=''):
	tl = [text]

	try:
		for ln in traceback.format_exc().split('\n'):
			if ln:
				tl.append('\t' + ln)
	except Exception:
		pass

	if len(tl) > 1 and not tl[0]:
		tl[0] = tl[-1].strip()

	error(domain, '\n'.join(tl))

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
				'%d/%d, %s: %s' % (i, len(dl), pfx, d.key),
				d.text,
				'started: %s' % d.started,
				'elapsed: %s' % (dt - d.started),
			])
	else:
		ents = [['', 'There are no active tasks']]

	return (ents, lambda i, _: taskd.cancel(m.get(i, '')))

status = StatusMgr()

taskd = TaskMgr(status, key=KEY_TASK)
status.link(taskd)

errord = Drawer(status, key=KEY_ERROR, timeout=TIMEOUT_ERROR)
status.link(errord)

noted = Drawer(status, key=KEY_NOTE, timeout=TIMEOUT)
status.link(noted)

status.start()
