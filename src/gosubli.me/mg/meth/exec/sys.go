// +build !windows

package exec

import (
	"fmt"
	"os"
	"os/exec"
	"strings"
	"syscall"
)

func kill(c *exec.Cmd) error {
	return syscall.Kill(-c.Process.Pid, syscall.SIGKILL)
}

func interrupt(c *exec.Cmd) error {
	return syscall.Kill(-c.Process.Pid, syscall.SIGINT)
}

func setsid(c *exec.Cmd) {
	if c.SysProcAttr == nil {
		c.SysProcAttr = &syscall.SysProcAttr{}
	}
	c.SysProcAttr.Setsid = true
}

func maxRss(p *os.ProcessState) string {
	if p != nil {
		if ru, ok := p.SysUsage().(*syscall.Rusage); ok {
			// is this multiplier correct on OS X?
			return fmtBytes(ru.Maxrss * 1024)
		}
	}
	return ""
}

func fmtBytes(n int64) string {
	l := make([]string, 0, 4)
	pairs := []struct {
		s string
		n int64
	}{
		{"G", 1 << 30},
		{"M", 1 << 20},
		{"K", 1 << 10},
		{"B", 1},
	}

	for _, p := range pairs {
		if n >= p.n {
			l = append(l, fmt.Sprintf("%d%s", n/p.n, p.s))
			n %= p.n
		}
	}

	if len(l) > 0 {
		return strings.Join(l, ", ")
	}
	return "0B"
}
