await backend.subscribe(["foo", "bar"])  # subscribe to two channels
await backend.publish(
    b"something", ["foo"]
)  # publish a message to a channel we're subscribed to

# start the stream after publishing. Depending on the backend
# the previously published message might be in the stream
event_generator = backend.stream_events()

# unsubscribe from the channel we previously published to
await backend.unsubscribe(["foo"])

# this should block, as we expect messages from channels
# we unsubscribed from to not appear in the stream anymore
print(anext(event_generator))