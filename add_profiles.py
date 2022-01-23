# %%
import requests
from dotenv import load_dotenv
import os, json, re, shutil
from random import randint
import configparser

load_dotenv()
config = configparser.ConfigParser()

# %%
router_url = os.environ['ROUTER_URL']
directory_name = input("Directory Path: ")
delete_response = input("Do you want to purge all current files? (y/n): ")
user_input_name = input('What do you want to name these profiles? ')
login_response = requests.get('http://{router_url}/api/router/login'.format(router_url=router_url), params={"pwd": os.environ['glinet_p']})
token = json.loads(login_response.text)['token']

# %%
# Option to purge all
if delete_response == "y":
	purge_response = requests.get('http://{router_url}/cgi-bin/api/wireguard/client/alldelete'.format(router_url=router_url), \
		headers={'Authorization': token})
	print("Purged all current profiles")
elif delete_response == '':
	exit()

# %%
directory = os.fsencode(directory_name)

for file in os.listdir(directory):
    file_path = os.fsdecode(file)
    if file_path.startswith('.'):
            continue

    listen_port = randint(51820, 65535)
    server_name = user_input_name + "_" + re.findall('-([^.]+).', file_path)[0]
    config.read_file(open(directory_name + '/' + file_path))
    # Interface Vars
    private_key = config.get('Interface', 'PrivateKey')
    address = config.get('Interface', 'Address')
    dns = config.get('Interface', 'DNS')
    # Peer Vars
    public_key = config.get('Peer', 'PublicKey')
    allowed_ips = config.get('Peer', 'AllowedIPs')
    end_point = config.get('Peer', 'Endpoint')

    params = {
            "name": server_name,
            "listen_port": listen_port,
            "private_key": private_key,
            "dns": dns,
            "end_point": end_point,
            "public_key": public_key,
            "allowed_ips": allowed_ips,
            "persistent_keepalive": '25',
            "address": address
            }

    client_add_response = requests.post('http://{router_url}/cgi-bin/api/wireguard/client/add'.format(router_url=router_url), \
    headers={'Authorization': token}, data = params
    )
    post_response = json.loads(client_add_response.text)['code']

    if post_response != 0:
        print(client_add_response.text)
        exit()

shutil.rmtree(directory_name)