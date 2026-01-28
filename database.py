import pymysql

# 数据库配置
DB_CONFIG = {
    'host': '192.168.133.120',
    'user': 'root',
    'password': '123456', # 记得填你的密码
    'database': 'weather_project',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

# 注册用户逻辑
def add_user(username, password):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # 存入用户，默认角色是 user
            sql = "INSERT INTO users (username, password, role) VALUES (%s, %s, 'user')"
            cursor.execute(sql, (username, password))
        conn.commit()
        return True
    except Exception as e:
        print(f"数据库注册错误: {e}")
        return False
    finally:
        conn.close()

# 登录验证逻辑
def verify_user(username, password):
    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM users WHERE username=%s AND password=%s"
            cursor.execute(sql, (username, password))
            return cursor.fetchone() # 找到返回用户信息，找不到返回 None
    finally:
        conn.close()