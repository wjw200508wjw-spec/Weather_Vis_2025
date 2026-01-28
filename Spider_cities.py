import requests
from bs4 import BeautifulSoup
import pymysql
import time

# --- 配置区 ---
DB_CONFIG = {
    'host': '192.168.133.120',  # 你的虚拟机IP
    'user': 'root',
    'password': '123456',      # 记得改成你设置的密码，如 123456
    'database': 'weather_project',
    'charset': 'utf8mb4'
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def init_city_table():
    url = "https://lishi.tianqi.com/"
    print(f"开始请求城市列表页面: {url}")
    
    try:
        # 1. 获取页面内容
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.encoding = 'utf-8'
        if response.status_code != 200:
            print(f"页面请求失败，状态码: {response.status_code}")
            return

        # 2. 解析 HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 准确定位：主页上 A-Z 字母下的城市链接都在 ._ex 结构中
        city_links = soup.select('.table_list a')
        
        if not city_links:
            print("未找到城市链接，请检查 HTML 结构是否变化。")
            return

        print(f"成功解析到 {len(city_links)} 个城市链接，准备入库...")

        # 3. 连接数据库入库
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        success_count = 0
        for link in city_links:
            city_name = link.text.strip()
            # href 示例: "/beijing/" -> 提取出 "beijing"
            href = link.get('href', '')
            # 1. 先把 index.html 和 index.htm 这种后缀全杀掉
            temp_pinyin = href.replace('index.html', '').replace('index.htm', '')
            
            # 2. 再把多余的符号（斜杠、点）全杀掉
            city_pinyin = temp_pinyin.replace('/', '').replace('.', '').strip()
            
            # 过滤掉空的
            if not city_pinyin or city_pinyin == '#': 
                continue

            try:
                # 使用 INSERT IGNORE 防止重复插入
                sql = "INSERT IGNORE INTO cities (city_name, city_pinyin) VALUES (%s, %s)"
                cursor.execute(sql, (city_name, city_pinyin))
                success_count += cursor.rowcount
            except Exception as e:
                print(f"插入城市 {city_name} 失败: {e}")

        conn.commit()
        print(f"--- 处理完成 ---")
        print(f"实际新增城市数量: {success_count}")
        
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"发生错误: {e}")

if __name__ == "__main__":
    init_city_table()