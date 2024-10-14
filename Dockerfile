FROM python:3.12-alpine
WORKDIR /app
ADD requirements.txt .
RUN pip install -r requirements.txt
ADD . .
CMD ["python3", "bot.py"]