FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# استخدام بورت Railway الديناميكي المعتمد لضمان عمل التطبيق بدون مشاكل
CMD streamlit run app.py --server.port=${PORT:-8501}
