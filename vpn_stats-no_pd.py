from speedtest import Speedtest, ConfigRetrievalError
import requests, json, os
from dotenv import load_dotenv
#from tqdm import tqdm
import mariadb
import sys

load_dotenv()

router_url = os.environ['ROUTER_URL']
def get_token(router_url):
    login_response = requests.get('http://{router_url}/api/router/login'.format(router_url=router_url), params={"pwd": os.environ['glinet_p']})
    token = json.loads(login_response.text)['token']
    return token

token = get_token(router_url)
# %%
client_list = \
    requests.get('http://{router_url}/cgi-bin/api/wireguard/client/list'.format(router_url=router_url), \
		headers={'Authorization': token})
client_peers = [ sub['name'] for sub in json.loads(client_list.text)['peers'] ]
# Stop any running VPN processes
requests.get('http://{router_url}/cgi-bin/api/wireguard/client/stop'.format(router_url=router_url), \
		headers={'Authorization': token})
# %%
name_list = []
ping_list = []
download_list = []
upload_list = []
for client in client_peers:
#for client in tqdm(client_peers):
    switch_request = \
        requests.post('http://{router_url}/cgi-bin/api/wireguard/client/start'.format(router_url=router_url), \
            headers={'Authorization': token}, \
            data={"name": client}
        )
    if json.loads(switch_request.text)['code'] == -1:
        token = get_token(router_url)
        switch_request = \
            requests.post('http://{router_url}/cgi-bin/api/wireguard/client/start'.format(router_url=router_url), \
                headers={'Authorization': token}, \
                data={"name": client}
            )
        if json.loads(switch_request.text)['code'] != 0:
            raise BaseException
    elif json.loads(switch_request.text)['code'] != 0:
        raise BaseException
    
    try:
        s = Speedtest()
        s.download()
        s.upload()
        name_list.append(client)
        ping_list.append(s.results.dict()['ping'])
        download_list.append(s.results.dict()['download'] / 1000000)
        upload_list.append(s.results.dict()['upload'] / 1000000)
    except ConfigRetrievalError:
        name_list.append(client)
        ping_list.append(0)
        download_list.append(0)
        upload_list.append(0)

best_vpn = name_list[ping_list.index(min(ping_list))]

requests.post('http://{router_url}/cgi-bin/api/wireguard/client/start'.format(router_url=router_url), \
    headers={'Authorization': token}, \
    data={"name": best_vpn}
)
print('Changed VPN to {client}'.format(client=best_vpn))

# Connect to MariaDB Platform
try:
    conn = mariadb.connect(
        user=os.environ["USER"],
        password=os.environ["PASSWORD"],
        host=os.environ["HOST"],
        port=os.environ["PORT"],
        database=os.environ["DATABASE"]

    )
except mariadb.Error as e:
    print(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

cur = conn.cursor()

# Execute Commands
cur.execute(
    "TRUNCATE vpn_stats"
)

for index in enumerate(name_list):
    cur.execute(
        "INSERT INTO vpn_stats (Name, Ping, Download, Upload) VALUES ('{n}', {p}, {d}, {u})".format(
        n=name_list[index], p=round(ping_list[index],2), \
        d=round(download_list[index],2), u=round(upload_list[index],2)
        )
    )

conn.commit()
cur.close()