FROM python:3.6.5
ADD . /app
WORKDIR /app
RUN pip install -r requeriments.txt
EXPOSE 8000
RUN source .env
CMD python -m http.server &; python run.py