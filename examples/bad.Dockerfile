# DO NOT COPY THIS FILE. It is the "spot the mistakes" exercise for lab 3.
# Almost every line breaks a rule from the course. Run:
#   python -m dockerhygiene.cli check examples/bad.Dockerfile
FROM python
ENV API_KEY=replace-me
RUN apt-get update && apt-get install -y curl
WORKDIR /app
ADD . /app
RUN pip install -r app/requirements.txt
EXPOSE 8080
CMD python app/server.py
