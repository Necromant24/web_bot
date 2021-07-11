FROM python:latest

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /
COPY static/. /
COPY data_files/. /

EXPOSE 5000
EXPOSE 5500

CMD ["python", "./main.py"]