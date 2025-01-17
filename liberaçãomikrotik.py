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
        # Determina o tipo de conteúdo recebido
        if request.content_type == 'application/json':
            data = request.json
        else:
            data = request.form.to_dict()

        # Verifica se os dados foram enviados
        if not data:
            return jsonify({"success": False, "message": "Nenhum dado enviado"}), 400

        # Log dos headers e dados recebidos (para depuração)
        print("Headers recebidos:", request.headers)
        print("Dados recebidos:", data)

        # Extração dos dados importantes
        payment_id = data.get('id')  # ID do pagamento
        status = data.get('status')  # Status do pagamento
        external_reference = data.get('external_reference')  # Referência externa contendo múltiplas variáveis

        if not payment_id or not status or not external_reference:
            return jsonify({"success": False, "message": "Dados incompletos na notificação"}), 400

        # Decodifica o external_reference assumindo que ele é um JSON string
        try:
            external_data = json.loads(external_reference)
            mac_address = external_data.get('mac')  # Obtém o MAC Address
            duration = external_data.get('duration')  # Obtém a duração
        except (ValueError, TypeError):
            # Caso o external_reference não seja JSON, trate como string simples
            print("Formato inválido em external_reference:", external_reference)
            mac_address, duration = None, None

        if not mac_address or not duration:
            return jsonify({"success": False, "message": "Dados incompletos em external_reference"}), 400

        # Processa a notificação com base no status
        if status == 'approved':
            print(f"Pagamento aprovado! ID: {payment_id}, MAC: {mac_address}, Duração: {duration}")
            # Adiciona o MAC ao IP Binding com a duração especificada
            add_mac_to_ip_binding(mac_address, duration)
        elif status == 'pending':
            print(f"Pagamento pendente. ID: {payment_id}, MAC: {mac_address}, Duração: {duration}")
            # Lógica para pagamentos pendentes (opcional)
        elif status == 'rejected':
            print(f"Pagamento rejeitado. ID: {payment_id}, MAC: {mac_address}, Duração: {duration}")
            # Lógica para pagamentos rejeitados (opcional)
        else:
            print(f"Status desconhecido: {status}. ID: {payment_id}, Referência: {external_reference}")

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
