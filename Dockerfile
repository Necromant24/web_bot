
FROM nginx
FROM digglerz/python3.8

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /
COPY static/. /
COPY data_files/. /
COPY data_files/nginx.conf /conf/nginx.conf

EXPOSE 5000
EXPOSE 5500
EXPOSE 4400

CMD ["python", "./main.py"]