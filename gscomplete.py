from gosubl import cfg
from gosubl import ev
from gosubl import gs
from gosubl import mg9
from gosubl import vu
from os.path import basename
from os.path import dirname
import gspalette
import json
import os
import re
import sublime
import sublime_plugin

AC_OPTS = sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS
REASONABLE_PKGNAME_PAT = re.compile(r'^\w+$')

last_gopath = ''
END_SELECTOR_PAT = re.compile(r'.*?((?:[\w.]+\.)?(\w+))$')
START_SELECTOR_PAT = re.compile(r'^([\w.]+)')
DOMAIN = 'GsComplete'
SNIPPET_VAR_PAT = re.compile(r'\$\{([a-zA-Z]\w*)\}')

HINT_KEY = '%s.completion-hint' % DOMAIN

BUILD_TAGS = [
	'386',
	'arm',
	'cgo',
	'darwin',
	'dragonfly',
	'freebsd',
	'go1',
	'go1.1',
	'go1.2',
	'ignore',
	'linux',
	'netbsd',
	'netgo',
	'openbsd',
	'plan9',
	'race',
	'windows',
]
BUILD_CL = [(tag, tag) for tag in BUILD_TAGS]

def snippet_match(ctx, m):
	try:
		for k,p in m.get('match', {}).items():
			q = ctx.get(k, '')
			if p and gs.is_a_string(p):
				if not re.search(p, str(q)):
					return False
			elif p != q:
				return False
	except:
		gs.notice(DOMAIN, gs.traceback())
	return True

def expand_snippet_vars(vars, text, title, value):
	sub = lambda m: vars.get(m.group(1), '')
	return (
		SNIPPET_VAR_PAT.sub(sub, text),
		SNIPPET_VAR_PAT.sub(sub, title),
		SNIPPET_VAR_PAT.sub(sub, value)
	)

def resolve_snippets(ctx):
	cl = set()
	types = [''] if ctx.get('local') else ctx.get('types')
	vars = {}
	for k,v in ctx.items():
		if gs.is_a_string(v):
			vars[k] = v

	try:
		snips = []
		snips.extend(cfg.default_snippets)
		snips.extend(cfg.snippets)
		for m in snips:
			try:
				if snippet_match(ctx, m):
					for ent in m.get('snippets', []):
						text = ent.get('text', '')
						title = ent.get('title', '')
						value = ent.get('value', '')
						if text and value:
							for typename in types:
								vars['typename'] = typename
								if typename:
									if len(typename) > 1 and typename[0].islower() and typename[1].isupper():
										vars['typename_abbr'] = typename[1].lower()
									else:
										vars['typename_abbr'] = typename[0].lower()
								else:
									vars['typename_abbr'] = ''

								txt, ttl, val = expand_snippet_vars(vars, text, title, value)
								s = u'%s\t%s \u0282' % (txt, ttl)
								cl.add((s, val))
			except:
				gs.notice(DOMAIN, gs.traceback())
	except:
		gs.notice(DOMAIN, gs.traceback())
	return list(cl)

class GoSublime(sublime_plugin.EventListener):
	INTERFACES = []
	gocode_set = False
	current_interface = {'name': '', 'funcs': []}
	not_in_scope = False
	def on_query_completions(self, view, prefix, locations):
		pos = locations[0]
		scopes = view.scope_name(pos).split()
		self.not_in_scope = ('source.go' not in scopes) or (gs.setting('gscomplete_enabled', False) is not True)
		if self.not_in_scope:
			return []

		if view.score_selector(pos, 'comment.build-constraint.go') > 0:
			return (BUILD_CL, AC_OPTS)

		if not scope_ok(view, pos):
			return ([], AC_OPTS)

		try:
			if basename(view.file_name()) == "main.go":
				default_pkgname = 'main'
			else:
				default_pkgname = basename(dirname(view.file_name()))
		except Exception:
			default_pkgname = ''

		if not REASONABLE_PKGNAME_PAT.match(default_pkgname):
			default_pkgname = ''

		offset = pos - len(prefix)
		vv = vu.V(view)
		src = vv.src()

		if not src:
			return ([], AC_OPTS)

		intel, _ = mg9.bcall('intel', {
			'Fn': vv.vfn(),
			'Src': src,
			'Pos': pos,
		})

		pkgname = intel.get('Pkg')
		if not default_pkgname:
			default_pkgname = pkgname if pkgname else 'main'

		types = intel.get('Types')  or []
		ctx = {
			'global': intel.get('Global'),
			'local': not intel.get('Global'),
			'pkgname': pkgname,
			'types': types or [''],
			'has_types': len(types) > 0,
			'default_pkgname': default_pkgname,
			'fn': vv.fn(),
		}

		if not pkgname:
			return (resolve_snippets(ctx), AC_OPTS) if cfg.autocomplete_snippets else ([], AC_OPTS)

		iface_name = view.substr(view.line(sublime.Region(pos -1 , pos)))[:-1]
		if iface_name.rfind('.') != -1:
			iface_name = iface_name[iface_name.rfind('.') + 1:]

		if iface_name != GoSublime.current_interface['name']:
			GoSublime.current_interface = {'name': iface_name, 'funcs': []}

		nc = view.substr(sublime.Region(pos, pos+1))
		cl = self.complete(vv.fn() or '<stdin>', offset, src, nc.isalpha() or nc == "(")

		pc = view.substr(sublime.Region(pos-1, pos))
		if cfg.autocomplete_snippets and (pc.isspace() or pc.isalpha()):
			if scopes[-1] == 'source.go':
				cl.extend(resolve_snippets(ctx))
			elif scopes[-1] == 'meta.block.go' and ('meta.function.plain.go' in scopes or 'meta.function.receiver.go' in scopes):
				cl.extend(resolve_snippets(ctx))
		return (cl, AC_OPTS)

	def find_end_pt(self, view, pat, start, end, flags=sublime.LITERAL):
		r = view.find(pat, start, flags)
		return r.end() if r and r.end() < end else -1

	def suggest(self, sl):
		if not sl:
			return

		def f(i, win):
			if i < 0:
				return

			gspalette.toggle_import((win.active_view(), {
				'path': sl[i],
				'add': True,
			}))

		gs.show_quick_panel(sl, f)

	def on_text_command(self, view, command_name, args):
		if self.not_in_scope or command_name != 'commit_completion':
			return
		view.run_command('run_macro_file', {"file": "res://Packages/Default/Delete Line.sublime-macro"})
		GoSublime.current_interface = {'name': '', 'funcs': [], 'view': None}

	def complete(self, fn, offset, src, func_name_only):
		comps = []
		autocomplete_tests = gs.setting('autocomplete_tests', False)
		autocomplete_closures = gs.setting('autocomplete_closures', False)
		res, err = mg9.complete(fn, src, offset)
		if err:
			gs.notice(DOMAIN, err)

		ents = res['Candidates']
		if not ents and gs.setting('autocomplete_suggest_imports') is True:
			self.suggest(res['Suggestions'])

		name_fx = None
		name_fx_pat = gs.setting('autocomplete_filter_name')
		if name_fx_pat:
			try:
				name_fx = re.compile(name_fx_pat)
			except Exception as ex:
				gs.notice(DOMAIN, 'Cannot filter completions: %s' % ex)

		in_iface = GoSublime.current_interface['name'] in GoSublime.INTERFACES and src[offset-1:offset] == '.'
		for ent in ents:
			if name_fx and name_fx.search(ent['name']):
				continue

			tn = ent['type']
			cn = ent['class']
			nm = ent['name']
			is_func = (cn == 'func')
			is_func_type = (cn == 'type' and tn.startswith('func('))
			
			if cn == 'type' and tn == 'interface' and nm not in GoSublime.INTERFACES:
				GoSublime.INTERFACES.append(nm)

			if in_iface:
				tmpl = '//Implementing %s·%s\nfunc (${1:this} ${2:*struct_name}) %s%s {\n\t$0\n}\n'
				if cn == 'func' and tn != 'built-in':
					sig = tmpl % (GoSublime.current_interface['name'], nm, nm, tn[4:])
					GoSublime.current_interface['funcs'].append(sig)

			if is_func:
				if nm in ('main', 'init'):
					continue

				if not autocomplete_tests and nm.startswith(('Test', 'Benchmark', 'Example')):
					continue

			if is_func or is_func_type:
				s_sfx = u'\u0282'
				t_sfx = gs.CLASS_PREFIXES.get('type', '')
				f_sfx = gs.CLASS_PREFIXES.get('func', '')
				params, ret = declex(tn)
				decl = []
				for i, p in enumerate(params):
					n, t = p
					if t.startswith('...'):
						n = '...'
					decl.append('${%d:%s}' % (i+1, n))
				decl = ', '.join(decl)
				ret = ret.strip('() ')

				if is_func:
					if func_name_only:
						comps.append((
							'%s\t%s %s' % (nm, ret, f_sfx),
							nm,
						))
					else:
						comps.append((
							'%s\t%s %s' % (nm, ret, f_sfx),
							'%s(%s)' % (nm, decl),
						))
				else:
					comps.append((
						'%s\t%s %s' % (nm, tn, t_sfx),
						nm,
					))

					if autocomplete_closures:
						comps.append((
							'%s {}\tfunc() {...} %s' % (nm, s_sfx),
							'%s {\n\t${0}\n}' % tn,
						))
			elif cn != 'PANIC':
				comps.append((
					'%s\t%s %s' % (nm, tn, self.typeclass_prefix(cn, tn)),
					nm,
				))
		if len(GoSublime.current_interface['funcs']) > 0 :
			comps.insert(0,('Implement Interface','\n'.join(GoSublime.current_interface['funcs']) + '\n'))
		else:
			self.not_in_scope = True
			# GoSublime.current_interface = []

		return comps

	def typeclass_prefix(self, typeclass, typename):
		return gs.NAME_PREFIXES.get(typename, gs.CLASS_PREFIXES.get(typeclass, ' '))

ignored_scope_names = ', '.join([
	'comment.block.go',
	'comment.line.double-slash.go',
	'string.quoted.double.go',
	'string.quoted.raw.go',
	'constant.other.rune.go',
])

def scope_ok(view, pos):
	if view.score_selector(pos, ignored_scope_names) != 0:
		# if moving left takes us out of scope then we're not between the delims.
		# due to the way the syntax is defined, going to the righ of end delim takes us of scope,
		# even if we're still touching it
		return view.score_selector(pos-1, ignored_scope_names) == 0

	return True

def declex(s):
	params = []
	ret = ''
	if s.startswith('func('):
		lp = len(s)
		sp = 5
		ep = sp
		dc = 1
		names = []
		while ep < lp and dc > 0:
			c = s[ep]
			if dc == 1 and c in (',', ')'):
				if sp < ep:
					n, _, t = s[sp:ep].strip().partition(' ')
					t = t.strip()
					if t:
						for name in names:
							params.append((name, t))
						names = []
						params.append((n, t))
					else:
						names.append(n)
					sp = ep + 1
			if c == '(':
				dc += 1
			elif c == ')':
				dc -= 1
			ep += 1
		ret = s[ep:].strip() if ep < lp else ''
	return (params, ret)

def _ct(view):
	if not gs.is_go_source_view(view):
		return

	if gs.setting('calltips') is True:
		view.run_command('gs_show_call_tip', {'set_status': True})
	else:
		view.erase_status(HINT_KEY)

class GsShowCallTip(sublime_plugin.TextCommand):
	def is_enabled(self):
		return gs.is_go_source_view(self.view)

	def run(self, edit, set_status=False):
		view = self.view
		vv = vu.V(view)
		fn = vv.vfn()
		src = vv.src()
		pos = vv.sel().begin()

		def f(cl, err):
			def f2(cl, err):
				c = {}
				if len(cl) == 1:
					c = cl[0]

				if set_status:
					intel, _ = mg9.bcall('intel', {
						'Fn': fn,
						'Src': src,
						'Pos': pos,
					})

					s = ''
					if c:
						pfx = 'func('
						typ = c['type']
						if typ.startswith(pfx):
							s = 'func %s(%s' % (c['name'], typ[len(pfx):])
						else:
							s = '%s: %s' % (c['name'], typ)

					func = intel.get('Func')
					if func:
						s = u'%s \u00B7 %s > %s' % (s, intel.get('Pkg'), func)

					if s:
						view.set_status(HINT_KEY, s)
					else:
						view.erase_status(HINT_KEY)
				else:
					if c:
						s = '%s %s\n%s' % (c['name'], c['class'], c['type'])
					else:
						s = '// %s' % (err or 'No calltips found')

					gs.show_output(HINT_KEY, s, print_output=False, syntax_file='GsDoc')

			sublime.set_timeout(lambda: f2(cl, err), 0)

		mg9.calltip(fn, src, pos, set_status, f)


if not gs.checked(DOMAIN, '_ct'):
	ev.cursor_moved += _ct
