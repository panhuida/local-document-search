import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# 加载 .env 文件
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

# 获取数据库连接字符串
db_url = os.environ.get('DATABASE_URL')
if not db_url:
    print("Error: DATABASE_URL not found in .env file.")
    exit(1)

try:
    # 创建数据库引擎
    engine = create_engine(db_url)
    with engine.connect() as connection:
        # 使用事务执行 DROP TABLE 命令
        with connection.begin():
            print("Dropping table 'documents'...")
            connection.execute(text("DROP TABLE IF EXISTS documents;"))
            print("Table 'documents' dropped successfully.")
except Exception as e:
    print(f"An error occurred: {e}")
