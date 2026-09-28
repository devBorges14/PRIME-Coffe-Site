from flask import (
    flash,
    jsonify,
    render_template,
    request
)

from werkzeug.exceptions import HTTPException

try:
    from flask_wtf.csrf import CSRFError
except ImportError:  # pragma: no cover
    CSRFError = None


# Caminhos consumidos pelo JavaScript do site público: para
# eles, erros voltam em JSON (o script.js espera JSON), não
# em página HTML.

JSON_PATHS = ("/contato", "/disponibilidade")


def wants_json():
    return request.path.startswith(JSON_PATHS)


# =========================================================
# HEADERS DE SEGURANÇA
# =========================================================

def register_security_headers(app):

    @app.after_request
    def add_security_headers(response):

        # Impede o navegador de "adivinhar" o tipo do arquivo
        response.headers.setdefault(
            "X-Content-Type-Options",
            "nosniff"
        )

        # Impede que o site seja aberto dentro de um iframe
        # de outro site (clickjacking)
        response.headers.setdefault(
            "X-Frame-Options",
            "DENY"
        )

        # Não vaza a URL completa para sites externos
        response.headers.setdefault(
            "Referrer-Policy",
            "strict-origin-when-cross-origin"
        )

        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=()"
        )

        # Páginas do admin nunca ficam em cache: depois do
        # logout, o botão "voltar" não mostra dados de clientes.
        if request.path.startswith("/admin"):
            response.headers["Cache-Control"] = "no-store"

        return response


# =========================================================
# PÁGINAS / RESPOSTAS DE ERRO
# =========================================================

ERROR_TEXTS = {
    400: (
        "Requisição inválida",
        "Não foi possível processar o pedido. "
        "Volte e tente novamente."
    ),
    403: (
        "Acesso negado",
        "Você não tem permissão para acessar esta página."
    ),
    404: (
        "Página não encontrada",
        "O endereço que você tentou acessar não existe."
    ),
    405: (
        "Ação não permitida",
        "Esta ação não é permitida neste endereço."
    ),
    413: (
        "Envio grande demais",
        "O conteúdo enviado ultrapassa o tamanho permitido."
    ),
    429: (
        "Muitas tentativas",
        "Você fez muitas tentativas em pouco tempo. "
        "Aguarde alguns minutos e tente novamente."
    ),
    500: (
        "Algo deu errado",
        "Ocorreu um erro inesperado. "
        "Tente novamente em alguns instantes."
    ),
}


def _render_error(code, message_override=None):

    title, message = ERROR_TEXTS.get(
        code,
        ERROR_TEXTS[500]
    )

    if message_override:
        message = message_override

    if wants_json():

        return jsonify({
            "success": False,
            "errors": [message]
        }), code

    return render_template(
        "error.html",
        code=code,
        title=title,
        message=message
    ), code


def register_error_handlers(app):

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):

        code = error.code or 500

        # Login bloqueado por excesso de tentativas: volta
        # para a própria tela de login, com aviso.
        if code == 429 and request.path == "/admin/login":

            flash(
                ERROR_TEXTS[429][1],
                "error"
            )

            return render_template(
                "admin/login.html"
            ), 429

        return _render_error(code)

    if CSRFError is not None:

        @app.errorhandler(CSRFError)
        def handle_csrf_error(error):

            return _render_error(
                400,
                "Sua sessão expirou ou a página ficou aberta por "
                "muito tempo. Recarregue a página e tente novamente."
            )

    # Em desenvolvimento NÃO registramos o handler genérico:
    # assim o Flask continua mostrando o depurador com o
    # traceback completo, que é o que queremos ao programar.
    # Em produção, o usuário só vê a página genérica e o erro
    # completo vai para o log.

    if app.config.get("IS_PRODUCTION"):

        @app.errorhandler(Exception)
        def handle_unexpected_error(error):

            app.logger.exception(
                "Erro inesperado em %s %s",
                request.method,
                request.path
            )

            return _render_error(500)
