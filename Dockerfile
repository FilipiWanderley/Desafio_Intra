FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY data/input ./data/input
ENTRYPOINT ["intra-ai"]
CMD ["analyze", "data/input", "--output", "outputs"]
