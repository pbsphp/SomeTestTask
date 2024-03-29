import codecs
import ConfigParser
import functools

import markdown
import openstack
from flask import Flask, g, jsonify, request
from keystoneauth1 import session
from keystoneauth1.identity import v3

config = ConfigParser.RawConfigParser()
config.read('project.conf')
if not config:
    raise RuntimeError('missing project.conf')

app = Flask(__name__)
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = config.getboolean('app', 'pretty_json')


def keystoneauth(fn):
    """Authenticate user and add connection and session info to `g'.
    """
    @functools.wraps(fn)
    def _inner(*args, **kwargs):
        username = request.headers.get('X-Keystone-Username')
        password = request.headers.get('X-Keystone-Password')

        if not username or not password:
            resp = jsonify({
                'success': False,
                'message': 'Auth failed: X-Keystone-Username and X-Keystone-Password headers are required',
            })
            return resp, 401

        auth = v3.Password(
            auth_url=config.get('keystoneauth', 'auth_url'),
            username=username,
            password=password,
            project_name=config.get('keystoneauth', 'project_name'),
            user_domain_id=config.get('keystoneauth', 'user_domain_id'),
            project_domain_id=config.get('keystoneauth', 'project_domain_id'),
        )
        sess = session.Session(auth=auth)
        conn = openstack.connection.Connection(
            session=sess,
            region_name=config.get('keystoneauth', 'region_name'),
        )

        g.conn = conn
        response = fn(*args, **kwargs)
        g.conn = None

        return response

    return _inner


@app.route('/')
def index():
    with codecs.open('README.md', encoding="utf-8") as f:
        return markdown.markdown(f.read())


@app.route('/servers', methods=['GET'])
@keystoneauth
def servers_list():
    def get_addr_data(all_data, kind):
        return {
            'version': all_data.get('version'),
            'addr': all_data.get('addr'),
            'kind': kind,
        }

    data = []
    for server in g.conn.compute.servers():
        addr_data = []
        for kind in ('public', 'private', 'shared'):
            addr = server.addresses.get(kind)
            if addr:
                addr_data.extend(get_addr_data(x, kind) for x in addr)

        data.append({
            'name': server.name,
            'addresses': addr_data,
            'description': server.description,
            'image_id': server.image_id,
            'status': server.status,
            'vm_state': server.vm_state,
            'volume_ids': [x['id'] for x in server.attached_volumes]
        })

    return jsonify(data)


@app.route('/servers/create', methods=['POST'])
@keystoneauth
def servers_create():
    params = request.json

    try:
        image_id = params['image_id']
        flavor_id = params['flavor_id']
        network_id = params['network_id']
        server_name = params['server_name']
    except KeyError:
        resp = jsonify({
            'success': False,
            'message': 'missing required param',
        })
        return resp, 422

    g.conn.compute.create_server(
        name=server_name,
        image_id=image_id,
        flavor_id=flavor_id,
        networks=[{"uuid": network_id}],
        availability_zone='nova',
    )

    return jsonify({
        'success': True,
    })


@app.route('/servers/<server_name>', methods=['DELETE'])
@keystoneauth
def servers_delete(server_name):
    server = g.conn.compute.find_server(server_name)
    if server is not None:
        g.conn.compute.delete_server(server)

    return jsonify({
        'success': True,
    })


@app.route('/images', methods=['GET'])
@keystoneauth
def images_list():
    data = []
    for image in g.conn.compute.images():
        data.append({
            'id': image.id,
            'name': image.name,
            'links': image.links,
            'status': image.status,
            'size': image.size,
        })

    return jsonify(data)


@app.route('/flavors', methods=['GET'])
@keystoneauth
def flavors_list():
    data = []
    for flavor in g.conn.compute.flavors():
        data.append({
            'id': flavor.id,
            'name': flavor.name,
            'description': flavor.description,
            'ram': flavor.ram,
            'vcpus': flavor.vcpus,
            'disk': flavor.disk,
        })

    return jsonify(data)


@app.route('/networks', methods=['GET'])
@keystoneauth
def networks_list():
    data = []
    for network in g.conn.network.networks():
        data.append({
            'id': network.id,
            'name': network.name,
            'status': network.status,
            'addr': network.location.cloud,
        })

    return jsonify(data)


if __name__ == '__main__':
    app.run(
        debug=config.getboolean('flask', 'debug'),
        host=config.get('flask', 'host'),
        port=config.getint('flask', 'port'),
    )
