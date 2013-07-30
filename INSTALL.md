Installation
============

Dependencies
------------

Non-python tools:

  * MongoDB 2.4.5 (http://www.mongodb.org/)
  * Redis 2.6.14 (http://redis.io/)
  * libevent 2.0.21 (http://libevent.org/)

Python tools:

  * MongoKit 0.8.0
  * Flask 0.10
  * Pandas 0.12.0 (http://pandas.pydata.org/)
  * gevent (http://www.gevent.org/)
  * Python-RQ (http://python-rq.org/)

Steps
-----

Install MongoDB, Redis, and libevent.

Install virtualenv.

    pip install virtualenv

Create and activate a new virtual environment.

    virtualenv GAUSS
    source GAUSS/bin/activate

Install remaining Python packages.

    pip install mongokit
    pip install flask
    pip install pandas
    pip install gevent
    pip install rq

Start Redis.

    redis-server &

Start Flask.

    python code/app.py

Navigate to the [local web server address](http://localhost:5000/).
