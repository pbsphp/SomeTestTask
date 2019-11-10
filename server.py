import ConfigParser

from flask import Flask, jsonify, request

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


@app.route('/servers', methods=['GET'])
def servers_list():
    conn = get_openstack_connection()
    data = []
    for server in conn.compute.servers():
        addrs = server.addresses.get('public', [])

        data.append({
            'name': server.name,
            'addresses': [x['addr'] for x in addrs],
            'description': server.description,
            'image_id': server.image_id,
            'status': server.status,
            'vm_state': server.vm_state,
            'volume_ids': [x['id'] for x in server.attached_volumes]
        })

    # TODO: Fix manual json serialization
    # TODO: Add Content-Type: application/json header.
    return jsonify(data)


@app.route('/servers/create', methods=['POST'])
def servers_create():
    conn = get_openstack_connection()
    params = request.json

    try:
        image_id = params['image_id']
        flavor_id = params['flavor_id']
        network_id = params['network_id']
        server_name = params['server_name']
    except KeyError:
        return jsonify({
            'success': False,
            'message': 'missing required param',
        })

    conn.compute.create_server(
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
def servers_delete(server_name):
    conn = get_openstack_connection()

    server = conn.compute.find_server(server_name)
    if server is not None:
        conn.compute.delete_server(server)

    return jsonify({
        'success': True,
    })


@app.route('/images', methods=['GET'])
def images_list():
    conn = get_openstack_connection()
    data = []

    for image in conn.compute.images():
        data.append({
            'id': image.id,
            'name': image.name,
            'links': image.links,
            'status': image.status,
            'size': image.size,
        })

    return jsonify(data)


@app.route('/flavors', methods=['GET'])
def flavors_list():
    conn = get_openstack_connection()
    data = []

    for flavor in conn.compute.flavors():
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
def networks_list():
    conn = get_openstack_connection()
    data = []

    for network in conn.network.networks():
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
