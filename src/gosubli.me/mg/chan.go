package mg

type Chan string

func (c Chan) Send(data interface{}) {
	post(Response{
		Token: string(c),
		Data:  data,
	})
}
