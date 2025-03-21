# 删除Flask相关导入
import os
import sqlite3
import schedule
import time
import logging
import traceback  # 添加在文件顶部导入区域
import os
from datetime import datetime
from scipy.io import savemat  # 新增MAT文件支持
from flask import Flask, render_template
from flask import send_file  # 添加send_file导入
from selenium import webdriver
# 更新DeepSeek导入
# 修正DeepSeek导入方式
import requests  # 替换原有deepseek导入
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

# 数据库初始
def init_db():
    with sqlite3.connect('exchange_rates.db') as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS rates
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
             rate REAL NOT NULL,
             timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)
        ''')
        conn.commit()

# 配置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# 初始化Flask应用
app = Flask(__name__)

# 设置API配置
API_URL = "https://api.deepseek.com/v1/chat/completions"
API_KEY = 'sk-8d906d88d79b4a5f82ddc54d365d63bd'  # 保留原有API密钥
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# 使用DeepSeek提取511090
def extract_rate_with_gpt(text):
    try:
        logging.info('开始调用DeepSeek API进行提取')
        # 使用新的API调用方式
        data = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": 
                "你是一个专业提取30年国债ETF实时价格的工具。请从文本中识别最新价格（格式如：101.23），仅返回数字。若无有效数据返回'无法找到'。特别注意'最新价'、'当前价'等关键词。"},
                {"role": "user", "content": text}
            ],
            "temperature": 0
        }
        response = requests.post(API_URL, headers=HEADERS, json=data)
        response.raise_for_status()  # 检查HTTP错误
        
        result = response.json()
        rate_text = result["choices"][0]["message"]["content"].strip()
        
        logging.info(f'DeepSeek返回的文本: {rate_text}')
        if rate_text == '无法找到':
            raise ValueError('无法从文本中提取出有效的汇率数值')
        return float(rate_text)
    except Exception as e:
        logging.error(f'DeepSeek提取汇率失败: {str(e)}')
        raise

# 获取汇率数据
def get_exchange_rate():
    # 保持原有配置代码
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--log-level=3')
        
        # 增强图形渲染配置
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-gpu-sandbox')  # 新增沙盒限制解除
        chrome_options.add_argument('--use-angle=swiftshader')  # 使用软件渲染引擎
        chrome_options.add_argument('--disable-accelerated-2d-canvas')  # 禁用2D加速
        chrome_options.add_argument('--disable-webgl')  # 保留原有WebGL禁用
        
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        time.sleep(2)  # 增加浏览器初始化等待
        
        logging.info('开始获取汇率数据')
        driver.get('https://q.stock.sohu.com/cn/511090/index.shtml')
        
        # 使用JavaScript直接获取页面数据
        page_text = driver.execute_script("return document.body.innerText")
        rate = extract_rate_with_gpt(page_text)
        
        # 验证汇率数值的合理性
        if rate < 1 or rate > 10000:
            raise ValueError(f'获取到的汇率值 {rate} 超出合理范围')
        
        # 存储到数据库
        with sqlite3.connect('exchange_rates.db') as conn:
            c = conn.cursor()
            c.execute('INSERT INTO rates (rate) VALUES (?)', (rate,))
            conn.commit()
        
        logging.info(f'成功更新汇率: {rate}')
        
    except Exception as e:
        logging.error(f'获取汇率时发生错误: {str(e)}')
        logging.error(f'错误类型: {type(e).__name__}')
        if driver:
            try:
                logging.error(f'当前页面标题: {driver.title}')
                logging.error(f'当前页面URL: {driver.current_url}')
            except:
                logging.error('无法获取页面信息')
        raise
    finally:
        if driver:
            driver.quit()
 

# 修改定时任务
def schedule_task():
    while True:
        try:
            schedule.every(1).hours.do(get_exchange_rate)
            # 移除ETF相关任务
            schedule.run_pending()
            time.sleep(60)
        except Exception as e:
            logging.error(f'定时任务异常: {str(e)}')
            time.sleep(300)

# 修改首页路由
@app.route('/')
def index():
    try:
        with sqlite3.connect('exchange_rates.db') as conn:
            c = conn.cursor()
            c.execute('SELECT rate, datetime(timestamp, "localtime") FROM rates ORDER BY timestamp DESC LIMIT 10')
            rates = c.fetchall()
        return render_template('index.html', rates=rates)
    except Exception as e:
        logging.error(f'获取数据失败: {str(e)}')
        return render_template('index.html', rates=[])

# 新增MAT文件导出路由
@app.route('/export_mat')
def export_to_mat():
    try:
        with sqlite3.connect('exchange_rates.db') as conn:
            c = conn.cursor()
            # 获取汇率数据
            c.execute('SELECT rate, datetime(timestamp, "localtime") FROM rates ORDER BY timestamp DESC')
            rate_results = c.fetchall()

            # 简化数据结构
            mat_data = {
                'exchange_rate': [row[0] for row in rate_results],
                'exchange_rate_timestamp': [row[1] for row in rate_results]
            }
            
            # 确保目录可写
            if not os.access(os.getcwd(), os.W_OK):
                raise PermissionError("当前目录不可写")
            
            filename = f"financial_data_{datetime.now().strftime('%Y%m%d%H%M%S')}.mat"
            filepath = os.path.join(os.getcwd(), filename)
            
            # 添加文件生成日志
            logging.info(f'开始生成MAT文件: {filepath}')
            savemat(filepath, mat_data)
            logging.info(f'文件生成成功: {filepath} (大小: {os.path.getsize(filepath)} bytes)')
            
            response = send_file(
                filepath,
                as_attachment=True,
                download_name=filename
            )
            response.call_on_close(lambda: os.remove(filepath))
            return response
            
    except Exception as e:
        logging.error(f'导出失败: {str(e)}\n{traceback.format_exc()}')  # 添加详细错误堆栈
        return "文件导出失败，请查看服务器日志", 500


        
if __name__ == '__main__':
    try:
        init_db()
        # 先获取一次初始数据
        get_exchange_rate()
        
        # 恢复多线程定时任务
        import threading
        scheduler_thread = threading.Thread(target=schedule_task)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        # 恢复Flask启动
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logging.error(f'程序启动失败: {str(e)}')
        raise