import re
import sublime

ANN = 'a13.07.29-1'
VERSION = 'r13.07.29-1'
DEFAULT_GO_VERSION = 'go?'
GO_VERSION_OUTPUT_PAT = re.compile(r'go\s+version\s+(\S+(?:\s+[+]\w+|\s+\([^)]+)?)', re.IGNORECASE)
GO_VERSION_NORM_PAT = re.compile(r'[^\w.+-]+', re.IGNORECASE)
PLATFORM = '%s-%s' % (sublime.platform(), sublime.arch())
