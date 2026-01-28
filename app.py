from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import pymysql
from database import add_user, verify_user 

app = Flask(__name__)
app.secret_key = 'weather_vis_final_key' 

# 数据库配置
DB_CONFIG = {
    'host': '192.168.133.120',
    'user': 'root',
    'password': '123456',
    'database': 'weather_project',
    'charset': 'utf8mb4'
}

def get_db_conn():
    return pymysql.connect(**DB_CONFIG)

# --- 路由 ---

@app.route('/')
def index():
    if 'username' in session:
        if session['username'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        return render_template('index.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']
        if verify_user(user, pwd):
            session['username'] = user
            if user == 'admin':
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('index'))
        else:
            flash("用户名或密码错误")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']
        if add_user(user, pwd):
            flash("注册成功")
            return redirect(url_for('login'))
        else:
            flash("用户已存在")
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# 管理员后台
@app.route('/admin')
def admin_dashboard():
    if session.get('username') != 'admin':
        return "<h1>403 禁止访问</h1><p>请用 admin 账号登录</p>", 403
    
    conn = get_db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username FROM users")
    users = cursor.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

# 修改密码 
@app.route('/api/request_password_change', methods=['POST'])
def request_password_change():
    if 'username' not in session: return jsonify({'code': 401})
    new_pwd = request.json.get('new_password')
    username = session['username']
    
    try:
        conn = get_db_conn(); c = conn.cursor()
        c.execute("SELECT password FROM users WHERE username=%s", (username,))
        row = c.fetchone()
        if row and row[0] == new_pwd:
            conn.close()
            return jsonify({'code': 400, 'msg': '新密码不能和旧密码一样'})
        
        c.execute("UPDATE users SET password=%s WHERE username=%s", (new_pwd, username))
        conn.commit(); conn.close()
        return jsonify({'code': 200, 'msg': '✅ 密码修改成功！'})
    except Exception as e:
        return jsonify({'code': 500, 'msg': str(e)})

# 城市列表
@app.route('/api/cities')
def get_cities_list():
    query = request.args.get('q', '').strip()
    conn = get_db_conn()
    cursor = conn.cursor()
    data = []
    
    try:
        if not query:
            # 这里的拼音列表对应：北京, 上海, 广州, 深圳, 成都, 杭州, 重庆, 西安, 武汉, 南京
            hot_pinyin = ['beijing', 'shanghai', 'guangzhou', 'shenzhen', 'chengdu', 'hangzhou', 'chongqing', 'xian', 'wuhan', 'nanjing']
            
            # 动态生成 SQL: city_pinyin IN ('beijing', 'shanghai', ...)
            pinyin_str = "'" + "','".join(hot_pinyin) + "'"
            sql = f"SELECT city_name, city_pinyin, province FROM cities WHERE city_pinyin IN ({pinyin_str})"
            
            cursor.execute(sql)
            rows = cursor.fetchall()
            
            # 如果拼音也没查到，则返回前20个城市
            if not rows:
                cursor.execute("SELECT city_name, city_pinyin, province FROM cities LIMIT 20")
                rows = cursor.fetchall()
        else:
            # 搜索逻辑保持不变
            cursor.execute("SELECT city_name, city_pinyin, province FROM cities WHERE city_name LIKE %s OR city_pinyin LIKE %s LIMIT 50", (f"%{query}%", f"%{query}%"))
            rows = cursor.fetchall()
        
        # 格式化数据，防止 province 为空报错
        data = [{'name':r[0], 'pinyin':r[1], 'province':r[2] or '未知'} for r in rows]
        
    except Exception as e:
        print(f"查询出错: {e}")
        data = []
    finally:
        conn.close()
        
    return jsonify({'code': 200, 'data': data})

# 地图数据
@app.route('/api/map_data')
def get_map_data():
    try:
        conn=get_db_conn(); c=conn.cursor()
        c.execute("SELECT province, AVG(avg_max_temp) FROM cities c JOIN weather_details w ON c.city_pinyin=w.city_pinyin GROUP BY province")
        data = [{'name':r[0],'value':round(float(r[1]),1)} for r in c.fetchall() if r[0]]
        conn.close()
        return jsonify({'code':200, 'data':data})
    except:
        return jsonify({'code':200, 'data':[]})

# 详情
@app.route('/api/weather')
def get_city_weather():
    try:
        city=request.args.get('city'); conn=get_db_conn(); c=conn.cursor()
        c.execute("SELECT month_date,avg_max_temp,avg_min_temp,ext_max_temp,ext_min_temp FROM weather_details WHERE city_pinyin=%s ORDER BY month_date",(city,))
        rows=c.fetchall(); conn.close()
        return jsonify({'code':200,'data':{'dates':[str(r[0]) for r in rows],'avg_max':[r[1] for r in rows],'avg_min':[r[2] for r in rows],'table_data':[{'date':str(r[0]),'avg_max':r[1],'avg_min':r[2],'ext_max':r[3],'ext_min':r[4]} for r in rows]}})
    except:
        return jsonify({'code':404})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)