import pymysql
import cpca

# --- 数据库配置 (保持不变) ---
db_config = {
    'host': '192.168.133.120',
    'user': 'root',
    'password': '123456',
    'database': 'weather_project',
    'charset': 'utf8mb4'
}

def fill_provinces_data():
    conn = pymysql.connect(**db_config)
    cursor = conn.cursor()

    print("🚀 开始读取城市数据 (智能重试版)...")
    
    # 1. 选出所有还没填省份的城市
    sql_select = "SELECT id, city_name FROM cities WHERE province IS NULL OR province = ''"
    cursor.execute(sql_select)
    rows = cursor.fetchall()
    
    print(f"📋 共找到 {len(rows)} 个待处理城市")

    updates = []
    
    # 定义我们要尝试的后缀顺序
    # 优先试“县”和“区”，因为很多名字像“长安”既是区也是古代的市
    suffixes = ["市", "县", "区", "旗", "自治县", ""]

    for row in rows:
        city_id = row[0]
        raw_name = row[1]
        
        found_province = None
        
        # 🔄 智能循环：依次给名字加上不同的尾巴试试
        for suffix in suffixes:
            search_name = raw_name + suffix
            
            # 只有当名字只有2个字时，才必须加后缀，防止"安新"这种被误判
            # 如果名字已经很长（如阿巴嘎），可能不需要后缀也能识别，或者需要特定的后缀
            
            try:
                df = cpca.transform([search_name])
                province = df.iloc[0]['省']
                
                if province:
                    # 找到了！
                    # 特殊修正：直辖市
                    if province in ['北京市', '上海市', '天津市', '重庆市']:
                        province = province # 保持原样
                    
                    found_province = province
                    # print(f"   ✅ 识别成功: {raw_name} (+{suffix}) -> {province}")
                    break # 找到了就停止尝试，跳出后缀循环
            except:
                continue

        if found_province:
            updates.append((found_province, city_id))
        else:
            # 实在找不到，试试兜底逻辑：有些名字可能是简称，比如 "阿盟" -> "阿拉善盟"
            # 这里如果不处理，就留空，回头手动改那几个少数的
            print(f"⚠️ 彻底无法识别: {raw_name}")

        # 每积累 100 条打印一次进度
        if len(updates) % 100 == 0 and len(updates) > 0:
            print(f"   ⏳ 已准备更新 {len(updates)} 条数据...")

    # 3. 批量写入
    if updates:
        print(f"💾 正在将 {len(updates)} 条省份数据写入数据库...")
        sql_update = "UPDATE cities SET province = %s WHERE id = %s"
        cursor.executemany(sql_update, updates)
        conn.commit()
        print("✅ 省份补全完成！快去数据库看看吧！")
    else:
        print("没有数据被更新。")

    conn.close()

if __name__ == "__main__":
    fill_provinces_data()