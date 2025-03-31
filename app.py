from flask import Flask
import config
from blueprints.auth import auth_bp
from blueprints.admin import admin_bp
from blueprints.user_conduct import user_conduct_bp
from blueprints.user_subjects import user_subjects_bp
from blueprints.summary import summary_bp

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Đăng ký các Blueprint
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(user_conduct_bp, url_prefix='/conduct')
app.register_blueprint(user_subjects_bp, url_prefix='/subjects')
app.register_blueprint(summary_bp, url_prefix='/summary')

if __name__ == '__main__':
    app.run(debug=True)
    app.run(debug=True)