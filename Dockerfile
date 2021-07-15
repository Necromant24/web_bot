FROM digglerz/python3.8

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /
COPY static/. /
COPY data_files/. /

EXPOSE 5000 5500 4400


CMD ["python", "./main.py"]