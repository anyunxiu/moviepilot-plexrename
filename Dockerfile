FROM python:3.12-slim

ENV LANG="C.UTF-8" \
    TZ="Asia/Shanghai" \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 3060
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3060"]
