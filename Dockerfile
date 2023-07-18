FROM python:3.9-alpine

WORKDIR /app

COPY dist/bandit-github-formatter-1.0.tar.gz bandit-github-formatter-1.0.tar.gz
RUN pip install pyyaml==6.0.1 bandit==1.7.0 requests==2.25.1 bandit-github-formatter-1.0.tar.gz
RUN rm bandit-github-formatter-1.0.tar.gz

COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
