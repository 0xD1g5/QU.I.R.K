FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "pymodbus>=3.8.0,<4"
COPY modbus_sim.py .
EXPOSE 502
CMD ["python", "modbus_sim.py"]
