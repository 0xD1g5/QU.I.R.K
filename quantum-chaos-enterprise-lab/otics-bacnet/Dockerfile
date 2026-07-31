FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "bacpypes3>=0.0.100,<0.1"
COPY bacnet_sim.py .
EXPOSE 47808/udp
CMD ["python", "bacnet_sim.py"]
