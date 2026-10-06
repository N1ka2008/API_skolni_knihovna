from flask import Flask
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)


def init_swagger(app):
    swagger = get_swaggerui_blueprint(
        "/docs",
        "/static/openapi.yaml",
        config={"app_name": "API školní knihovny"},
    )
    app.register_blueprint(swagger)


init_swagger(app)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8082)