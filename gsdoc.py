from gosubl import gs
from gosubl import gsq
from gosubl import kv
from gosubl import mg9
from gosubl import ui
from gosubl import vu
import os
import re
import sublime
import sublime_plugin

DOMAIN = 'GsDoc'

GOOS_PAT = re.compile(r'_(%s)' % '|'.join(gs.GOOSES))
GOARCH_PAT = re.compile(r'_(%s)' % '|'.join(gs.GOARCHES))
EXT_EXCLUDE = [
	'out', 'exe', 'o', 'dll', 'so', 'a', 'dynlib', 'lib', 'com', 'bin', 'pyc', 'pyo', 'cache', 'db',
	'bak', 'png', 'gif', 'jpeg', 'jpg', 'gz', 'zip', '7z', 'rar', 'tar', '1', '2', '3', 'old', 'tgz',
	'pprof', 'prof', 'mem', 'cpu', 'swap',
]

class GsPosdefCommand(sublime_plugin.TextCommand):
	def is_enabled(self):
		return bool(gs.is_go_source_view(self.view) and self.view.file_name())

	def run(self, _):
		view = self.view
		pt = gs.sel(view).begin()
		src = view.substr(sublime.Region(0, view.size()))
		pt = len(src[:pt].encode("utf-8"))
		def f(res, err):
			if err:
				ui.error(DOMAIN, err)
				return

			fn = res.get('Fn')
			row = res.get('Line', -1) - 1
			col = res.get('Col', 0) - 1
			if not fn or row < 0:
				ui.note(DOMAIN, "no definition found")
				return

			gs.println('opening %s:%s:%s' % (fn, row, col))
			vu.open(fn=fn, row=row, col=col)

		mg9.a_posdef(view.file_name(), pt, f)

class GsDocCommand(sublime_plugin.TextCommand):
	def is_enabled(self):
		return gs.is_go_source_view(self.view)

	def show_output(self, s):
		gs.show_output(DOMAIN+'-output', s, False, 'GsDoc')

	def run(self, _, mode=''):
		view = self.view
		if (not gs.is_go_source_view(view)) or (mode not in ['goto', 'hint']):
			return

		pt = gs.sel(view).begin()
		src = view.substr(sublime.Region(0, view.size()))
		pt = len(src[:pt].encode("utf-8"))
		def f(docs, err):
			doc = ''
			if err:
				self.show_output('// Error: %s' % err)
			elif docs:
				if mode == "goto":
					fn = ''
					flags = 0
					if len(docs) > 0:
						d = docs[0]
						fn = d.get('fn', '')
						row = d.get('row', 0)
						col = d.get('col', 0)
						if fn:
							gs.println('opening %s:%s:%s' % (fn, row, col))
							vu.open(fn=fn, row=row, col=col)
							return
					self.show_output("%s: cannot find definition" % DOMAIN)
				elif mode == "hint":
					s = []
					for d in docs:
						name = d.get('name', '')
						if name:
							kind = d.get('kind', '')
							pkg = d.get('pkg', '')
							if pkg:
								name = '%s.%s' % (pkg, name)
							src = d.get('src', '')
							if src:
								src = '\n//\n%s' % src
							doc = '// %s %s%s' % (name, kind, src)

						s.append(doc)
					doc = '\n\n\n'.join(s).strip()
			self.show_output(doc or "// %s: no docs found" % DOMAIN)

		mg9.doc(view.file_name(), src, pt, f)

class GsBrowseDeclarationsCommand(sublime_plugin.WindowCommand):
	def run(self, dir=''):
		if dir == '.':
			self.present_current()
		elif dir:
			self.present('', '', dir)
		else:
			def f(res, err):
				if err:
					ui.error(DOMAIN, err)
					return

				ents, m = handle_pkgdirs_res(res)
				if ents:
					ents.insert(0, "Current Package")

					def cb(i, win):
						if i == 0:
							self.present_current()
						elif i >= 1:
							self.present('', '', os.path.dirname(m[ents[i]]))

					gs.show_quick_panel(ents, cb)
				else:
					gs.show_quick_panel([['', 'No source directories found']])

			mg9.pkg_dirs(f)

	def present_current(self):
		vv = vu.V(gs.active_valid_go_view(win=self.window, strict=False))
		self.present(vv.vfn(), vv.src(), vv.dir())

	def present(self, vfn, src, pkg_dir):
		win = self.window
		if win is None:
			return

		def f(res, err):
			if err:
				ui.note(DOMAIN, err)
				return

			decls = res.get('file_decls', [])
			for d in res.get('pkg_decls', []):
				if not vfn or d['fn'] != vfn:
					decls.append(d)

			for d in decls:
				dname = (d['repr'] or d['name'])
				trailer = []
				trailer.extend(GOOS_PAT.findall(d['fn']))
				trailer.extend(GOARCH_PAT.findall(d['fn']))
				if trailer:
					trailer = ' (%s)' % ', '.join(trailer)
				else:
					trailer = ''
				d['ent'] = '%s %s%s' % (d['kind'], dname, trailer)

			ents = []
			for d in decls:
				ents.append(d['ent'])

			def cb(i, win):
				if i >= 0:
					d = decls[i]
					vu.open(fn=d['fn'], win=win, row=d['row'], col=d['col'])

			if ents:
				gs.show_quick_panel(ents, cb)
			else:
				gs.show_quick_panel([['', 'No declarations found']])

		mg9.declarations(vfn, src, pkg_dir, f)

def handle_pkgdirs_res(res):
	m = {}
	for root, dirs in res.items():
		for dir, fn in dirs.items():
			if not m.get(dir):
				m[dir] = fn
	ents = list(m.keys())
	ents.sort(key = lambda a: a.lower())
	return (ents, m)

class GsBrowsePackagesCommand(sublime_plugin.WindowCommand):
	def run(self):
		def f(res, err):
			if err:
				ui.error(DOMAIN, err)
				return

			ents, m = handle_pkgdirs_res(res)
			if ents:
				def cb(i, win):
					if i >= 0:
						dirname = gs.basedir_or_cwd(m[ents[i]])
						win.run_command('gs_browse_files', {'dir': dirname})
				gs.show_quick_panel(ents, cb)
			else:
				gs.show_quick_panel([['', 'No source directories found']])

		mg9.pkg_dirs(f)

def ext_filter(pathname, basename, ext):
	if not ext:
		return basename == "makefile"

	if ext in EXT_EXCLUDE:
		return False

	if ext.endswith('~'):
		return False

	return True

def show_pkgfiles(dirname, o=None):
	ents = []
	m = {}

	try:
		dirname = os.path.abspath(dirname)
		for fn in gs.list_dir_tree(dirname, ext_filter, gs.setting('fn_exclude_prefixes', []), o):
			name = os.path.relpath(fn, dirname).replace('\\', '/')
			m[name] = fn
			ents.append(name)
	except Exception as ex:
		ui.error(DOMAIN, 'Error: %s' % ex)

	if ents:
		ents.sort(key = lambda a: a.lower())

		try:
			s = " ../  ( current: %s )" % dirname
			m[s] = os.path.join(dirname, "..")
			ents.insert(0, s)
		except Exception:
			pass

		def cb(i, win):
			if i >= 0:
				fn = m[ents[i]]
				if os.path.isdir(fn):
					win.run_command("gs_browse_files", {"dir": fn})
				else:
					vu.open(fn=fn, win=win)
		gs.show_quick_panel(ents, cb)
	else:
		gs.show_quick_panel([['', 'No files found']])

class GsBrowseFilesCommand(sublime_plugin.WindowCommand):
	def run(self, dir=''):
		o = kv.O(cancelled=False)

		def cancel():
			o.cancelled = True

		if not dir:
			view = self.window.active_view()
			dir = gs.basedir_or_cwd(view.file_name() if view is not None else None)

		gsq.do(DOMAIN, lambda: show_pkgfiles(dir, o), 'scanning directory for package files', cancel=cancel)
