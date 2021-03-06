package exec

import (
	"gosubli.me/mg"
	"os/exec"
	"sync"
	"time"
)

type ProcTable struct {
	sync.Mutex

	m map[string]*exec.Cmd
}

var procs = NewProcTable()

func NewProcTable() *ProcTable {
	return &ProcTable{
		m: map[string]*exec.Cmd{},
	}
}

func (p *ProcTable) Run(cid string, cmd *exec.Cmd) (error, mg.MsDuration) {
	if cid == "" {
		cid = mg.Uid()
	}

	p.repl(cid, cmd)

	start := time.Now()
	setsid(cmd)
	err := cmd.Run()
	dur := mg.Since(start)

	p.Lock()
	delete(p.m, cid)
	p.Unlock()

	return err, dur
}

func (p *ProcTable) Cancel(cid string) {
	p.repl(cid, nil)
}

func (p *ProcTable) repl(cid string, cmd *exec.Cmd) {
	c := p.set(cid, cmd)
	if c == cmd {
		return
	}

	for i := 0; i < 2; i++ {
		c = p.set(cid, cmd)
		if c == cmd {
			break
		}
		interrupt(c)
		p.sleep()
	}

	for c != cmd {
		kill(cmd)
		p.sleep()
		c = p.set(cid, cmd)
	}
}

func (p *ProcTable) sleep() {
	time.Sleep(50 * time.Millisecond)
}

func (p *ProcTable) set(cid string, cmd *exec.Cmd) *exec.Cmd {
	p.Lock()
	defer p.Unlock()

	if c, ok := p.m[cid]; ok {
		return c
	}

	if cmd != nil {
		p.m[cid] = cmd
	}

	return cmd
}

func init() {
	mg.Defer(func() {
		procs.Lock()
		defer procs.Unlock()

		for _, c := range procs.m {
			if c != nil && c.Process != nil {
				c.Process.Kill()
				c.Process.Release()
			}
		}
	})
}
