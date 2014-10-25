package gs

import (
	"gosubli.me/mg"
)

var (
	statusChan  = mg.Chan("margo.status")
	errorDrawer = Drawer("margo.error")
	noteDrawer  = Drawer("margo.note")
)

type Drawer string

func (d Drawer) SetText(text string) {
	statusChan.Send(struct{ Key, Text string }{string(d), text})
}

func Error(text string) {
	errorDrawer.SetText(text)
}

func Note(text string) {
	noteDrawer.SetText(text)
}
