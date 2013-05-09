from fabric.api import run, env, sudo, settings
from fabric.contrib.files import exists

env.hosts = ['localhost']

def start():
    sudo(" ".join(["/Applications/mongodb/bin/mongod",
                  "--fork",
                  "--logpath /Volumes/achiever_vol2/mongod.log",
                  "--dbpath /Volumes/achiever_vol2/GAUSS"]),pty=False)

    run("/usr/local/bin/redis-server /Applications/redis/redis-2.6.13/redis.conf", pty=False)

    #rqworker_pid = run("nohup rqworker --path ~/cuttlefish/gauss/code/ 1> /Volumes/achiever_vol2/rqworker.stdout.log 2> /Volumes/achiever_vol2/rqworker.stderr.log < /dev/null &", pty=False)
    #with settings(warn_only=True):
    #    run("ps aux | grep rqworker | grep -v 'grep' | sed 's/\s\s*/ /g' | cut -d' ' -f4 > /Volumes/achiever_vol2/rqworker.pid")


def stop():
    
    with settings(warn_only=True):
        sudo("/usr/local/bin/redis-cli shutdown", pty=False)
        sudo("mongo --eval \"db.getSiblingDB('admin').shutdownServer()\"", pty=False)
        # if exists('/Volumes/achiever_vol2/rqworker.pid'):
        #     run('kill -HUP `cat /Volumes/achiever_vol2/rqworker.pid`')

def status():
    with settings(warn_only=True):
        run("ps aux | egrep 'rq|mongo|redis' | grep -v grep")