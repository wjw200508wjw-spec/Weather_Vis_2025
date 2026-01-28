import multiprocessing
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import pymysql
import time
import math

# --- 1. 数据库配置 ---
DB_CONFIG = {
    'host': '192.168.133.120',
    'user': 'root',
    'password': '123456',
    'database': 'weather_project',
    'charset': 'utf8mb4'
}

# --- 2. 爬虫配置 ---
TARGET_YEAR = "2025"
TARGET_XPATH = "/html/body/div[7]/div[1]/div[3]/ul"
MY_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36 Edg/144.0.0.0"

def get_conn():
    return pymysql.connect(**DB_CONFIG)

# --- 3. 核心工作进程 (接收驱动路径) ---
def worker(process_id, city_sub_list, driver_path): # 👈 新增 driver_path 参数
    print(f"🔥 进程-{process_id} 启动！")
    
    options = Options()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument(f'user-agent={MY_UA}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    
    # 窗口自动排版
    width = 800; height = 500
    if process_id == 0: x, y = 0, 0
    elif process_id == 1: x, y = 800, 0
    elif process_id == 2: x, y = 0, 500
    else: x, y = 800, 500

    try:
        # 🌟 直接使用主进程传过来的路径，不再下载！
        service = Service(executable_path=driver_path)
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"❌ 进程-{process_id} 驱动启动失败: {e}")
        return

    driver.set_window_rect(x=x, y=y, width=width, height=height)
    conn = get_conn()
    
    try:
        for idx, city in enumerate(city_sub_list):
            if idx % 10 == 0:
                print(f"   [P{process_id}] 进度: {idx}/{len(city_sub_list)}")

            for month in range(1, 13):
                url = f"https://lishi.tianqi.com/{city}/{TARGET_YEAR}{month:02d}.html"
                try:
                    driver.get(url)
                    time.sleep(1.0) 

                    # 只要 404，立刻跳过
                    if "404" in driver.title: continue

                    ul = driver.find_element(By.XPATH, TARGET_XPATH)
                    lis = ul.find_elements(By.TAG_NAME, "li")

                    if len(lis) >= 6:
                        # 拆解数据
                        li0_divs = lis[0].find_elements(By.CLASS_NAME, "tian_twoa")
                        val_avg_max = li0_divs[0].text.replace('℃','')
                        val_avg_min = li0_divs[1].text.replace('℃','')
                        val_ext_max = lis[1].find_element(By.CLASS_NAME, "tian_twoa").text.replace('℃','')
                        val_ext_min = lis[2].find_element(By.CLASS_NAME, "tian_twoa").text.replace('℃','')
                        val_avg_aqi = lis[3].find_element(By.CLASS_NAME, "tian_twoa").text
                        val_best_aqi = lis[4].find_element(By.CLASS_NAME, "tian_twoa").text
                        val_worst_aqi = lis[5].find_element(By.CLASS_NAME, "tian_twoa").text

                        sql = """INSERT INTO weather_details 
                                (city_pinyin, month_date, avg_max_temp, avg_min_temp, ext_max_temp, ext_min_temp, avg_aqi, best_aqi_val, worst_aqi_val) 
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                        
                        cursor = conn.cursor()
                        cursor.execute(sql, (city, f"{TARGET_YEAR}-{month:02d}-01", val_avg_max, val_avg_min, val_ext_max, val_ext_min, val_avg_aqi, val_best_aqi, val_worst_aqi))
                        conn.commit()
                except Exception:
                    continue
                    
    finally:
        conn.close()
        # driver.quit() # 注释掉这行，让窗口保留，方便你检查
        print(f"🏁 进程-{process_id} 完成！窗口保留中...")
        while True: time.sleep(10) # 保持窗口不关闭

if __name__ == "__main__":
    print("正在获取任务...")
    temp_conn = get_conn()
    cursor = temp_conn.cursor()
    cursor.execute("SELECT city_pinyin FROM cities")
    all_tasks = sorted(list(set([row[0].replace('/', '').replace('.html', '') for row in cursor.fetchall()])))
    temp_conn.close()
    
    # 🌟🌟🌟 关键修改：在主进程下载一次驱动，拿到路径 🌟🌟🌟
    print("📥 正在检查/下载 Chrome 驱动 (只需一次)...")
    DRIVER_PATH = ChromeDriverManager().install()
    print(f"✅ 驱动就绪: {DRIVER_PATH}")
    
    PROCESS_NUM = 4
    chunk_size = math.ceil(len(all_tasks) / PROCESS_NUM)
    processes = []

    print("🚀 正在启动 4 进程并行抓取...")
    for i in range(PROCESS_NUM):
        start = i * chunk_size
        end = min((i + 1) * chunk_size, len(all_tasks))
        sub_list = all_tasks[start:end]
        
        # 把 DRIVER_PATH 传进去
        p = multiprocessing.Process(target=worker, args=(i, sub_list, DRIVER_PATH))
        processes.append(p)
        p.start()
        time.sleep(2) # 间隔启动，防止瞬间卡死

    for p in processes:
        p.join()