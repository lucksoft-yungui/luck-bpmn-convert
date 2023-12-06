# 第一阶段：构建基础镜像，包含所有依赖
FROM python:3.8-slim as builder

# 设置工作目录
WORKDIR /app

# 将 requirements.txt 文件复制到容器中
COPY requirements.txt /app/

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 第二阶段：构建最终镜像
FROM python:3.8-slim

# 设置工作目录
WORKDIR /app

# 从 builder 阶段复制整个 Python 安装目录
COPY --from=builder /usr/local /usr/local
# 从 builder 阶段复制安装好的依赖
COPY --from=builder /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages

# 将 src 目录复制到容器中
COPY src/ /app/

# 创建上传目录
RUN mkdir /app/uploads

# 设置环境变量
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# 暴露端口 5000 供应用使用
EXPOSE 5000

# 运行应用
CMD ["flask", "run"]