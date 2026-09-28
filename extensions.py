from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


# Instância única do limitador de requisições, criada aqui
# (e não no app.py) para que os blueprints possam importá-la
# sem import circular.
#
# storage "memory://": os contadores ficam na memória do
# processo. Funciona bem com 1 processo; se um dia rodar com
# vários workers, trocar por Redis (ver Fase 9).

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri="memory://",
)
