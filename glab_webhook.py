import hmac
import hashlib
import json
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import os
import logging

# Configuración
PORT = 9000  # Puerto para el servidor webhook
SECRET_TOKEN = "tu_token_secreto_muy_seguro"  # Token secreto para verificar la solicitud
DEPLOY_SCRIPT = "/home/devcrack/PycharmProjects/simple_deploy/repo_path/deployment.sh"  # Ruta a tu script de despliegue
REPO_PATH = "/home/devcrack/PycharmProjects/simple_deploy/repo_path"  # Ruta a tu repositorio
TARGET_BRANCH = "main"  # La rama que quieres vigilar

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    # filename='/var/log/gitlab-webhook.log'
    filename="./logs/gitlab-webhook.log"
)
logger = logging.getLogger('gitlab-webhook')


class WebhookHandler(BaseHTTPRequestHandler):
    def _verify_signature(self, data):
        signature = self.headers.get('X-Gitlab-Token')
        if not signature:
            return False

        return signature == SECRET_TOKEN

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)

        # Verificar la firma
        if not self._verify_signature(post_data):
            self.send_response(403)
            self.end_headers()
            logger.warning("Solicitud rechazada: firma inválida")
            return

        # Procesar la solicitud
        try:
            payload = json.loads(post_data.decode('utf-8'))

            # Verificar que sea el evento y la rama correcta
            branch = payload.get('ref', '').replace('refs/heads/', '')

            if branch == TARGET_BRANCH:
                logger.info(
                    f"Evento recibido para la rama {TARGET_BRANCH}. Iniciando despliegue...")

                # Cambiar al directorio del repositorio
                os.chdir(REPO_PATH)

                # Ejecutar el script de despliegue
                result = subprocess.run([DEPLOY_SCRIPT],
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        text=True)

                if result.returncode == 0:
                    logger.info("Despliegue completado con éxito")
                    logger.debug(f"Salida: {result.stdout}")
                    print(f"{result.stdout}")
                else:
                    logger.error(f"Error en el despliegue: {result.stderr}")

                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'OK')
            else:
                logger.info(
                    f"Evento ignorado para rama {branch} (no es {TARGET_BRANCH})")
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'Ignored')

        except Exception as e:
            logger.error(f"Error al procesar la solicitud: {str(e)}")
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error: {str(e)}".encode('utf-8'))


if __name__ == "__main__":
    print("HI")
    server = HTTPServer(('0.0.0.0', PORT), WebhookHandler)
    logger.info(f"Servidor de webhook iniciado en el puerto {PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()
    logger.info("Servidor detenido")