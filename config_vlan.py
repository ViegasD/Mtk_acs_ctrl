from librouteros import connect

# Configurações do MikroTik
HOST = '192.168.88.1'  # IP do roteador MikroTik
USERNAME = 'admin'     # Usuário da API
PASSWORD = 'admin'     # Senha do usuário da API
PORT = 8728            # Porta da API do MikroTik

# Função para conectar ao MikroTik
def mikrotik_connect():
    try:
        return connect(username=USERNAME, password=PASSWORD, host=HOST, port=PORT)
    except Exception as e:
        print(f"Erro ao conectar ao MikroTik: {e}")
        return None

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

# Função principal para executar as configurações
if __name__ == '__main__':
    site_compra_ip = '203.0.113.10'  # IP do site de compra de acesso
    configure_firewall(site_compra_ip)
