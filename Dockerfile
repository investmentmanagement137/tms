FROM apify/actor-python-selenium:3.10

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . ./

CMD ["python", "src/main.py"]
