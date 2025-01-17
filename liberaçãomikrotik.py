from flask import Flask, request, jsonify
from librouteros import connect
import threading, json
import os
app = Flask(__name__)

# Configurações do MikroTik a partir de variáveis de ambiente
HOST = os.getenv('HOST')  # IP do roteador MikroTik
USERNAME = os.getenv('USERNAME')  # Usuário da API
PASSWORD = os.getenv('PASSWORD')  # Senha do usuário da API
PORT = int(os.getenv('PORT'))        # Porta da API do MikroTik

# Endpoint para receber notificações do Mercado Pago
@app.route('/payment-notification', methods=['POST'])
def payment_notification():
    try:
        # Log para verificar o endpoint foi acessado
        print("Endpoint acessado pelo Mercado Pago!")

        # Verifica o conteúdo enviado pelo Mercado Pago
        if request.content_type == 'application/json':
            data = request.json  # Tenta extrair o JSON diretamente
            print("JSON recebido:", data)
        else:
            return jsonify({"success": False, "message": "Conteúdo inválido"}), 400

        # Verifica se os dados foram enviados corretamente
        if not data:
            print("Nenhum dado recebido na notificação.")
            return jsonify({"success": False, "message": "Nenhum dado enviado"}), 400

        # Extração de informações da notificação
        action = data.get("action")  # Ação realizada (ex: payment.updated)
        notification_type = data.get("type")  # Tipo da notificação (ex: payment)
        payment_id = data.get("data", {}).get("id")  # ID do pagamento

        # Logs para depuração
        print(f"Ação: {action}, Tipo: {notification_type}, ID do pagamento: {payment_id}")

        # Validação dos dados extraídos
        if not action or not notification_type or not payment_id:
            print("Dados incompletos recebidos.")
            return jsonify({"success": False, "message": "Dados incompletos"}), 400

        # Processamento da notificação
        if notification_type == "payment" and action == "payment.updated":
            print(f"Pagamento atualizado! ID: {payment_id}")
        else:
            print(f"Notificação não tratada. Tipo: {notification_type}, Ação: {action}")

        # Responde ao Mercado Pago que a notificação foi processada
        return jsonify({"success": True, "message": "Notificação processada com sucesso"}), 200

    except Exception as e:
        print("Erro ao processar notificação:", str(e))
        return jsonify({"success": False, "message": "Erro ao processar notificação"}), 500




# Conexão ao MikroTik
def mikrotik_connect():
    try:
        return connect(username=USERNAME, password=PASSWORD, host=HOST, port=PORT)
    except Exception as e:
        print(f"Erro ao conectar ao MikroTik: {e}")
        return None


# Adicionar MAC ao IP Binding
def add_mac_to_ip_binding(mac_address, duration):
    api = mikrotik_connect()
    if not api:
        return False, "Erro ao conectar ao MikroTik"

    try:
        # Verificar se o MAC já está no IP Binding
        ip_bindings = api('/ip/hotspot/ip-binding/print')
        if any(binding['mac-address'] == mac_address for binding in ip_bindings):
            return False, f"MAC {mac_address} já está no IP Binding."

        # Adicionar o MAC ao IP Binding
        api('/ip/hotspot/ip-binding/add', **{
            'mac-address': mac_address,
            'type': 'bypassed',
            'comment': f'Acesso temporário VLAN Irrestrita ({duration} segundos)'
        })
        print(f"MAC {mac_address} movido para VLAN Irrestrita por {duration} segundos.")

        # Agendar remoção do MAC após o tempo especificado
        threading.Timer(duration, remove_mac_from_ip_binding, args=[mac_address]).start()
        return True, f"MAC {mac_address} adicionado com sucesso à VLAN Irrestrita."
    except Exception as e:
        return False, f"Erro ao adicionar MAC ao IP Binding: {e}"
    


# Remover MAC do IP Binding
def remove_mac_from_ip_binding(mac_address):
    api = mikrotik_connect()
    if not api:
        print(f"Erro ao conectar ao MikroTik para remover MAC {mac_address}.")
        return

    try:
        # Buscar o MAC no IP Binding e remover
        ip_bindings = api('/ip/hotspot/ip-binding/print')
        for binding in ip_bindings:
            if binding['mac-address'] == mac_address:
                api('/ip/hotspot/ip-binding/remove', **{'.id': binding['.id']})
                print(f"MAC {mac_address} removido do IP Binding.")
                break
    except Exception as e:
        print(f"Erro ao remover MAC {mac_address} do IP Binding: {e}")
    


# Endpoint para mover MAC para VLAN Irrestrita
@app.route('/add_mac', methods=['POST'])
def add_mac():
    data = request.json
    print(f"Requisição recebida: {data}")  # Log da requisição recebida

    mac_address = data.get('mac_address')
    duration = data.get('duration')  # Tempo em segundos enviado na requisição

    if not mac_address:
        return jsonify({"success": False, "message": "O campo 'mac_address' é obrigatório."}), 400

    if not duration or not isinstance(duration, int) or duration <= 0:
        return jsonify({"success": False, "message": "O campo 'duration' deve ser um número inteiro maior que zero."}), 400

    success, message = add_mac_to_ip_binding(mac_address, duration)
    status_code = 200 if success else 500
    return jsonify({"success": success, "message": message}), status_code


# Endpoint para remover MAC do IP Binding
@app.route('/remove_mac', methods=['POST'])
def remove_mac():
    data = request.json
    mac_address = data.get('mac_address')

    if not mac_address:
        return jsonify({"success": False, "message": "O campo 'mac_address' é obrigatório."}), 400

    try:
        remove_mac_from_ip_binding(mac_address)
        return jsonify({"success": True, "message": f"MAC {mac_address} removido com sucesso."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro ao remover MAC: {e}"}), 500


# Iniciar o servidor Flask
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
