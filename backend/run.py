from flask_cors import CORS

from app import create_app, db

app = create_app()
# 🔴 关键：全局开启跨域，支持所有请求头和方法
CORS(
    app,
    supports_credentials=True,
    origins="*",
    allow_headers=["*"],
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
)


@app.route("/")
def index():
    return {"status": "ok"}, 200


# 强制创建所有数据库表，避免注册时报表不存在
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
