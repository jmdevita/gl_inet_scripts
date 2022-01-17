from speedtest import Speedtest, ConfigRetrievalError
import requests, json, os
from dotenv import load_dotenv
import pandas as pd
from tqdm import tqdm

load_dotenv()

# %%
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

# %%
name_list = []
ping_list = []
download_list = []
upload_list = []
for client in tqdm(client_peers):
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

client_list = pd.DataFrame({
    "name": name_list,
    "ping": ping_list,
    "download": download_list,
    "upload": upload_list
})
client_list.to_csv('vpn_stats.csv')

best_vpn = name_list[ping_list.index(min(ping_list))]

requests.post('http://{router_url}/cgi-bin/api/wireguard/client/start'.format(router_url=router_url), \
    headers={'Authorization': token}, \
    data={"name": best_vpn}
)
print('Changed VPN to {client}'.format(client=best_vpn))
