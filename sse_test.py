import flask
import redis

app = flask.Flask(__name__)
red = redis.StrictRedis()

def event_stream():
    pubsub = red.pubsub()
    pubsub.subscribe('chat')
    # TODO: handle client disconnection.
    for message in pubsub.listen():
        print message
        yield 'data: %s\n\n' % message['data']

@app.route('/stream')
def stream():
    return flask.Response(event_stream(),
                          mimetype="text/event-stream")

@app.route('/')
def home():
    return """
        <!doctype html>
        <head>
        <title>chat</title>
        <script src="http://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js"></script>
        </head>
        <body>
        <pre id="out"></pre>
        <script>
            function sse() {
                var source = new EventSource('/stream');
                var out = document.getElementById('out');
                source.onmessage = function(e) {
                    // XSS in chat is fun
                    out.innerHTML =  e.data + '\\n' + out.innerHTML;
                };
            }
            sse();
        </script>
        </body>
        </html>

    """

if __name__ == '__main__':
    app.debug = True
    app.run()