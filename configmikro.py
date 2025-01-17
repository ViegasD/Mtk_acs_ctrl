from librouteros import connect
import os
# Configurações do MikroTik a partir de variáveis de ambiente
HOST = os.getenv('HOST', '192.168.88.1')  # IP do roteador MikroTik
USERNAME = os.getenv('USERNAME', 'admin')  # Usuário da API
PASSWORD = os.getenv('PASSWORD', 'admin')  # Senha do usuário da API
PORT = int(os.getenv('PORT', 8728))        # Porta da API do MikroTik

# Função para configurar regras de firewall
def configure_firewall(site_compra_ip):
    api = mikrotik_connect()
    if not api:
        return

    try:
        # Obter regras existentes para evitar duplicações
        firewall_rules = api('/ip/firewall/filter/print')

        # Regra 1: Permitir acesso ao site de compras na VLAN Restrita
        if not any(rule.get('comment') == 'Permitir acesso ao site de compra na VLAN Restrita' for rule in firewall_rules):
            api('/ip/firewall/filter/add', **{
                'chain': 'forward',
                'action': 'accept',
                'src-address': '192.168.10.0/24',
                'dst-address': site_compra_ip,
                'comment': 'Permitir acesso ao site de compra na VLAN Restrita'
            })
            print("Regra: Permitir acesso ao site de compra na VLAN Restrita adicionada.")

        # Regra 2: Bloquear todo o restante na VLAN Restrita
        if not any(rule.get('comment') == 'Bloquear acesso irrestrito na VLAN Restrita' for rule in firewall_rules):
            api('/ip/firewall/filter/add', **{
                'chain': 'forward',
                'action': 'drop',
                'src-address': '192.168.10.0/24',
                'comment': 'Bloquear acesso irrestrito na VLAN Restrita'
            })
            print("Regra: Bloquear acesso irrestrito na VLAN Restrita adicionada.")

        # Regra 3: Permitir acesso total na VLAN Irrestrita
        if not any(rule.get('comment') == 'Permitir acesso irrestrito na VLAN Liberada' for rule in firewall_rules):
            api('/ip/firewall/filter/add', **{
                'chain': 'forward',
                'action': 'accept',
                'src-address': '192.168.20.0/24',
                'comment': 'Permitir acesso irrestrito na VLAN Liberada'
            })
            print("Regra: Permitir acesso irrestrito na VLAN Liberada adicionada.")

        print("Regras de firewall configuradas com sucesso.")
    except Exception as e:
        print(f"Erro ao configurar firewall: {e}")
# Função para conectar ao MikroTik
def mikrotik_connect():
    try:
        return connect(username=USERNAME, password=PASSWORD, host=HOST, port=PORT)
    except Exception as e:
        print(f"Erro ao conectar ao MikroTik: {e}")
        return None

# Função para configurar a bridge e VLANs
def configure_bridge_and_vlans():
    api = mikrotik_connect()
    if not api:
        return

    try:
        # Criar Bridge
        print("Configurando a bridge...")
        bridges = api('/interface/bridge/print')
        if not any(bridge['name'] == 'bridge1' for bridge in bridges):
            api('/interface/bridge/add', **{'name': 'bridge1'})
            print("Bridge 'bridge1' criada com sucesso.")
        else:
            print("Bridge 'bridge1' já existe.")

        # Criar VLAN Restrita (VLAN 10)
        print("Configurando VLANs...")
        vlans = api('/interface/vlan/print')
        if not any(vlan['name'] == 'vlan-restrita' for vlan in vlans):
            api('/interface/vlan/add', **{
                'name': 'vlan-restrita',
                'vlan-id': '10',
                'interface': 'bridge1'
            })
            print("VLAN 'vlan-restrita' criada com sucesso.")
        else:
            print("VLAN 'vlan-restrita' já existe.")

        # Criar VLAN Liberada (VLAN 20)
        if not any(vlan['name'] == 'vlan-liberada' for vlan in vlans):
            api('/interface/vlan/add', **{
                'name': 'vlan-liberada',
                'vlan-id': '20',
                'interface': 'bridge1'
            })
            print("VLAN 'vlan-liberada' criada com sucesso.")
        else:
            print("VLAN 'vlan-liberada' já existe.")

        # Configurar endereços IP para as VLANs
        print("Configurando endereços IP...")
        ip_addresses = api('/ip/address/print')
        if not any(ip['address'].startswith('192.168.10.') for ip in ip_addresses):
            api('/ip/address/add', **{
                'address': '192.168.10.1/24',
                'interface': 'vlan-restrita'
            })
            print("Endereço IP configurado para 'vlan-restrita'.")

        if not any(ip['address'].startswith('192.168.20.') for ip in ip_addresses):
            api('/ip/address/add', **{
                'address': '192.168.20.1/24',
                'interface': 'vlan-liberada'
            })
            print("Endereço IP configurado para 'vlan-liberada'.")

        print("Configuração de bridge e VLANs concluída com sucesso.")
    except Exception as e:
        print(f"Erro ao configurar bridge e VLANs: {e}")

# Função para configurar o servidor DHCP para as VLANs
def configure_dhcp():
    api = mikrotik_connect()
    if not api:
        return

    try:
        # Configurar Pool de IP para VLAN Restrita
        print("Configurando servidor DHCP...")
        pools = api('/ip/pool/print')
        if not any(pool['name'] == 'dhcp_pool_vlan10' for pool in pools):
            api('/ip/pool/add', **{
                'name': 'dhcp_pool_vlan10',
                'ranges': '192.168.10.10-192.168.10.100'
            })
            print("Pool de IP 'dhcp_pool_vlan10' criado com sucesso.")

        # Configurar Pool de IP para VLAN Liberada
        if not any(pool['name'] == 'dhcp_pool_vlan20' for pool in pools):
            api('/ip/pool/add', **{
                'name': 'dhcp_pool_vlan20',
                'ranges': '192.168.20.10-192.168.20.100'
            })
            print("Pool de IP 'dhcp_pool_vlan20' criado com sucesso.")

        # Configurar DHCP Server para VLAN Restrita
        dhcp_servers = api('/ip/dhcp-server/print')
        if not any(dhcp['name'] == 'dhcp_vlan10' for dhcp in dhcp_servers):
            api('/ip/dhcp-server/add', **{
                'name': 'dhcp_vlan10',
                'interface': 'vlan-restrita',
                'address-pool': 'dhcp_pool_vlan10',
                'disabled': 'no'
            })
            print("Servidor DHCP 'dhcp_vlan10' configurado com sucesso.")

        # Configurar DHCP Server para VLAN Liberada
        if not any(dhcp['name'] == 'dhcp_vlan20' for dhcp in dhcp_servers):
            api('/ip/dhcp-server/add', **{
                'name': 'dhcp_vlan20',
                'interface': 'vlan-liberada',
                'address-pool': 'dhcp_pool_vlan20',
                'disabled': 'no'
            })
            print("Servidor DHCP 'dhcp_vlan20' configurado com sucesso.")

        print("Configuração de DHCP concluída com sucesso.")
    except Exception as e:
        print(f"Erro ao configurar DHCP: {e}")

# Configurar Hotspot na bridge1
def configure_hotspot():
    api = mikrotik_connect()
    if not api:
        return

    try:
        # Verificar se o Hotspot já está configurado
        hotspots = api('/ip/hotspot/print')
        if not hotspots:
            api('/ip/hotspot/setup', **{'interface': 'bridge1'})
            print("Hotspot configurado na interface 'bridge1'.")
        else:
            print("Hotspot já está configurado.")
    except Exception as e:
        print(f"Erro ao configurar o Hotspot: {e}")
    

# Função principal para executar as configurações
if __name__ == '__main__':
    configure_bridge_and_vlans()
    configure_dhcp()
    configure_hotspot()
    site_compra_ip = 'https://rmwifi.shop/'  # IP do site de compra de acesso
    configure_firewall(site_compra_ip)
