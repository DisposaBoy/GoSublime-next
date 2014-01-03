// +build !windows

package exec

import (
	"os/exec"
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
