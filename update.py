import requests, base64, json, re
from enum import Enum
import urllib.parse

class OutboundsProtocol(Enum):
    VMESS = 1
    VLESS = 2

used_protocol = OutboundsProtocol.VLESS

class VlessFormat:
    def __init__(self, uuid, address, port, parameters, fragment):
        self.uuid = uuid
        self.address = address
        self.port = port
        self.parameters = parameters
        self.fragment = fragment
    def __str__(self):
        return f"VlessFormat:\n\tuuid={self.uuid}\n\taddress={self.address}\n\tport={self.port}\n\tparameters={self.parameters}\n\tfragment={self.fragment}\n"

protocol_array = []

raw_vmess_list = []

vmess_json_list = []

raw_vless_list = []

vless_config_list = []

def get_context_of_subscription(sub_url):
    resp = requests.get(sub_url)
    protocol_urls = base64.b64decode(resp.content).decode("utf-8")
    print(protocol_urls)
    return protocol_urls

def is_vmess(url):
    us = re.split(r'://', url)
    return us[0] == "vmess"

def is_vless(url):
    us = re.split(r'://', url)
    return us[0] == "vless"


def parse_subscription(protocol_urls):
    global protocol_array
    global raw_vmess_list
    protocol_array = protocol_urls.splitlines()
    print(protocol_array)
    for url in protocol_array:
        if is_vmess(url):
            print(url)
            raw_vmess_list.append(url)
        elif is_vless(url):
            print(url)
            raw_vless_list.append(url)
        else:
            print("Unsupported protocols!\n")


def add_padding(raw_vmess):
    if len(raw_vmess) % 4 != 0:
        padding_count = 4 - len(raw_vmess) % 4
        raw_vmess = raw_vmess + '=' * padding_count
    return raw_vmess

def parse_vmess_to_json(url):
    raw_vmess = url[8:]
    raw_vmess = add_padding(raw_vmess)
    b_vmess = bytes(raw_vmess, encoding="utf-8")
    return json.loads(base64.b64decode(b_vmess).decode("utf-8"))

def parse_vless_parameters_to_dict(parameters):
    pdict = {}
    rest = parameters
    us = re.split(r'&', rest)
    for kv in us:
        kvs = re.split(r'=', kv)
        key = kvs[0]
        value = kvs[1]
        pdict[key] = value
    return pdict

def parse_vless_to_config(url):
    us = re.split(r'://', url)
    rest = us[1]
    us = re.split(r'@', rest)
    uuid = us[0]
    rest = us[1]
    us = re.split(r':', rest)
    address = us[0]
    rest = us[1]
    us = re.split(r'\?', rest)
    port = int(us[0])
    rest = us[1]
    us = re.split(r'#', rest)
    rawparameters = us[0]
    parameters = parse_vless_parameters_to_dict(rawparameters)
    fragment_encode = us[1]
    fragment = urllib.parse.unquote(fragment_encode)
    newconfig = VlessFormat(uuid, address, port, parameters, fragment)
    print(newconfig)
    return newconfig


def read_config_file(filename):
    with open(filename, "r") as f:
        config_json = json.loads(f.read())
        #print(config_json['outbounds'])
        return config_json

def update_vmess_outbounds_config(org_config, new_config):
    #print(org_config['outbounds'])
    tmp = org_config['outbounds']
    #for arg in tmp:
    #    print(arg)
    print(tmp[0]['settings']['vnext'][0])
    print(new_config['add'])
    print(type(tmp[0]['settings']['vnext'][0]['port']))
    print(type(new_config['port']))
    tmp[0]['settings']['vnext'][0]['address'] = new_config['add']
    tmp[0]['settings']['vnext'][0]['port'] = int(new_config['port'])
    tmp[0]['settings']['vnext'][0]['users'][0]['id'] = new_config['id']
    tmp[0]['settings']['vnext'][0]['users'][0]['alterId'] = new_config['aid']
    org_config['outbounds'] = tmp
    org_config = json.dumps(org_config, indent=4)
    return org_config

def update_vless_outbounds_config(org_config, newconfig):
    proxys = org_config['outbounds']
    proxy = proxys[0]
    proxy['mux']['concurrency'] = -1
    proxy['mux']['enabled'] = False
    proxy['protocol'] = "vless"
    proxy['tag'] = "proxy"
    proxy['settings']['vnext'][0]['address'] = newconfig.address
    proxy['settings']['vnext'][0]['port'] = newconfig.port
    proxy['settings']['vnext'][0]['users'][0]['id'] = newconfig.uuid
    proxy['settings']['vnext'][0]['users'][0]['level'] = 8
    for key, value in newconfig.parameters.items():
        if key == "encryption" or key == "flow":
            proxy['settings']['vnext'][0]['users'][0][key] = value
        elif key == "security":
            proxy['streamSettings'][key] = value
        elif key == "type":
            proxy['streamSettings']['network'] = value
        elif key == "sni":
            proxy['streamSettings']['realitySettings']['serverName'] = value
        elif key == "fp":
            proxy['streamSettings']['realitySettings']['fingerprint'] = value
        elif key == "pbk":
            proxy['streamSettings']['realitySettings']['publicKey'] = value
        elif key == "sid":
            proxy['streamSettings']['realitySettings']['shortId'] = value
        else:
            pass
    proxy['streamSettings']['realitySettings']['show'] = False
    proxy['streamSettings']['realitySettings']['allowInsecure'] = False
    proxy['streamSettings']['tcpSettings']['header']['type'] = "none"
    direct = proxys[1]
    direct['protocol'] = "freedom"
    direct['streamSettings']['network'] = "tcp"
    direct['streamSettings']['sockopt']['domainStrategy'] = "UseIP"
    direct['tag'] = "direct"
    blackhole = proxys[2]
    blackhole['protocol'] = "blackhole"
    blackhole['settings']['response']["type"] = "http"
    blackhole['tag'] = "block"
    newproxys = []
    newproxys.append(proxy)
    newproxys.append(direct)
    newproxys.append(blackhole)
    org_config['outbounds'] = newproxys
    print(org_config['outbounds'])
    return org_config

def add_udp_block_rule(rules):
    rule = {
        "network": "udp",
        "outboundTag": "block",
        "port": "443",
        "type": "field"
    }
    rules.append(rule)
    return rules

def update_vless_routeing_config(org_config, rules):
    routing_config = org_config['routing']
    routing_config['domainStrategy'] = "AsIs"
    routing_config['rules'] = rules
    org_config['routing'] = routing_config
    return org_config

def update_vless_config(org_config, newconfig):
    org_config['remarks'] = newconfig.fragment
    rules = []
    rules = add_udp_block_rule(rules)
    org_config = update_vless_routeing_config(org_config, rules)
    org_config = update_vless_outbounds_config(org_config, newconfig)
    org_config = json.dumps(org_config, indent=4)
    return org_config

if __name__ == '__main__':
    with open('subscription.txt', 'r') as f:
        jms_subscription = f.read()
    raw_content = get_context_of_subscription(jms_subscription)
    parse_subscription(raw_content)
    for raw in raw_vmess_list:
        vmess_json = parse_vmess_to_json(raw)
        print(vmess_json)
        vmess_json_list.append(vmess_json)
    for raw in raw_vless_list:
        vless_config = parse_vless_to_config(raw)
        vless_config_list.append(vless_config)

    if used_protocol == OutboundsProtocol.VMESS and len(vmess_json_list) > 0:
        local_config = read_config_file('config_vmess.json')
        new_config = update_vmess_outbounds_config(local_config, vmess_json_list[0])
        with open('config_new.json', 'w+') as f:
            f.write(new_config)
    elif used_protocol == OutboundsProtocol.VLESS and len(vless_config_list) > 0:
        local_config = read_config_file('config_vless.json')
        new_config = update_vless_config(local_config, vless_config_list[0])
        with open('config_new.json', 'w+') as f:
            f.write(new_config)
    else:
        pass
