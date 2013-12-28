package mg

import (
	"os"
	"os/exec"
	"sync"
	"time"
)

var (
	cmdWatchlist = map[string]*exec.Cmd{}
	cmdWatchLck  = sync.Mutex{}
)

type mKill struct {
	Cid string
}

func (m *mKill) Call() (res interface{}, err string) {
	res = M{
		m.Cid: killCmd(m.Cid),
	}
	return
}

func watchCmd(id string, c *exec.Cmd) bool {
	if id == "" {
		return false
	}

	cmdWatchLck.Lock()
	defer cmdWatchLck.Unlock()

	if _, ok := cmdWatchlist[id]; ok {
		return false
	}
	cmdWatchlist[id] = c
	return true
}

func unwatchCmd(id string) bool {
	if id == "" {
		return false
	}

	cmdWatchLck.Lock()
	defer cmdWatchLck.Unlock()

	if _, ok := cmdWatchlist[id]; ok {
		delete(cmdWatchlist, id)
		return true
	}
	return false
}

func killCmd(id string) bool {
	if id == "" {
		return false
	}

	cmdWatchLck.Lock()
	defer cmdWatchLck.Unlock()

	c, ok := cmdWatchlist[id]
	if !ok {
		return false
	}

	// the primary use-case for these functions are remote requests to cancel the process
	// so we won't remove it from the map

	c.Process.Signal(os.Interrupt)

	for i := 0; i < 10 && c.ProcessState == nil; i++ {
		time.Sleep(10 * time.Millisecond)
	}

	c.Process.Kill()

	// neither wait nor release are called because the cmd owner should be waiting on it
	return true
}

func init() {
	Defer(func() {
		cmdWatchLck.Lock()
		defer cmdWatchLck.Unlock()
		for _, c := range cmdWatchlist {
			c.Process.Kill()
			c.Process.Release()
		}
	})

	registry.Register("kill", func(b *Broker) Caller {
		return &mKill{}
	})

}
