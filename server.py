import ConfigParser

from flask import Flask

from keystoneauth1.identity import v3
from keystoneauth1 import session

import openstack

app = Flask(__name__)

config = ConfigParser.RawConfigParser()
config.read('project.conf')
if not config:
    raise RuntimeError('missing project.conf')


# TODO: Add keystone auth
def get_openstack_connection():
    auth = v3.Password(
        auth_url=config.get('keystoneauth', 'auth_url'),
        username=config.get('keystoneauth', 'username'),
        password=config.get('keystoneauth', 'password'),
        project_name=config.get('keystoneauth', 'project_name'),
        user_domain_id=config.get('keystoneauth', 'user_domain_id'),
        project_domain_id=config.get('keystoneauth', 'project_domain_id'),
    )
    sess = session.Session(auth=auth)

    conn = openstack.connection.Connection(
        session=sess,
        region_name='RegionOne',
    )

    return conn


@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    app.run(
        debug=config.getboolean('flask', 'debug'),
        host=config.get('flask', 'host'),
        port=config.getint('flask', 'port'),
    )
