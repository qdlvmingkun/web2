# 美元人民币汇率监控

这是一个自动获取并展示美元对人民币汇率的Web应用。该应用每天14:30自动从Google获取最新汇率数据，并通过网页展示历史汇率信息。

## 功能特点

- 自动获取美元对人民币汇率
- 定时任务（每天14:30更新）
- 数据持久化存储
- Web界面展示

## 安装要求

1. Python 3.7+
2. Chrome浏览器
3. ChromeDriver

## 安装步骤

1. 安装依赖包：
   ```
   pip install -r requirements.txt
   ```

2. 确保已安装Chrome浏览器和对应版本的ChromeDriver

## 运行应用

```
python app.py
```

启动后访问 http://localhost:5000 查看汇率数据。

## 注意事项

- 请确保网络连接正常
- 需要安装Chrome浏览器和ChromeDriver
- 程序会自动创建SQLite数据库文件