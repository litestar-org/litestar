# this file is used to create an image for running the docs.
FROM squidfunk/mkdocs-material

COPY requirements-docs.txt /

RUN pip install --upgrade pip && pip install --no-cache-dir -r /requirements-docs.txt

ENTRYPOINT ["mkdocs"]
