from litestar.channels import
subscriber = await channels.subscribe(["foo", "bar"])
# do some stuff here
await channels.unsubscribe(subscriber, ["foo"])
