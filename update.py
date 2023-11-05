import requests, base64, json


protocol_array = []

raw_vmess_list = []

vmess_json_list = []

def get_context_of_subscription(sub_url):
    resp = requests.get(sub_url)
    protocol_urls = base64.b64decode(resp.content).decode("utf-8")
    print(protocol_urls)
    return protocol_urls

def is_vmess(url):
    if (url[:8] == "vmess://"):
        return True
    else:
        return False

def parse_subscription(protocol_urls):
    global protocol_array
    global raw_vmess_list
    protocol_array = protocol_urls.splitlines()
    print(protocol_array)
    for url in protocol_array:
        if (is_vmess(url)):
            print(url)
            raw_vmess_list.append(url)
            

def add_padding(raw_vmess):
    if (len(raw_vmess) % 4 == 0):
        return raw_vmess
    else:
        padding_count = 4 - len(raw_vmess) % 4
        raw_vmess = raw_vmess + '=' * padding_count
        return raw_vmess
            
def parse_vmess_to_json(raw_vmess):
    raw_vmess = raw_vmess[8:]
    raw_vmess = add_padding(raw_vmess)
    b_vmess = bytes(raw_vmess, encoding="utf-8")
    vmess_json = json.loads(base64.b64decode(b_vmess).decode("utf-8"))
    return vmess_json


def read_config_file(filename):
    with open(filename, "r") as f:
        config_json = json.loads(f.read())
        #print(config_json['outbounds'])
        return config_json

def update_vmess_config(org_config, new_config):
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

if __name__ == '__main__':
    with open('subscription.txt', 'r') as f:
        jms_subscription = f.read()
    raw_content = get_context_of_subscription(jms_subscription)
    parse_subscription(raw_content)
    for raw in raw_vmess_list:
        vmess_json = parse_vmess_to_json(raw)
        print(vmess_json)
        vmess_json_list.append(vmess_json)

    local_config = read_config_file('config.json')
    new_config = update_vmess_config(local_config, vmess_json_list[2])
    with open('config_new.json', 'w+') as f:
        f.write(new_config)
