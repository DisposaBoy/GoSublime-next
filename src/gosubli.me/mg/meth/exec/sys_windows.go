// +build windows

package exec

import (
	"os"
	"os/exec"
)

func kill(c *exec.Cmd) error {
	return c.Process.Signal(os.Kill)
}

func interrupt(c *exec.Cmd) error {
	return c.Process.Signal(os.Interrupt)
}

func setsid(c *exec.Cmd) {
}
