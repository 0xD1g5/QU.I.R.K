FROM python:3.9-slim
RUN pip install --no-cache-dir \
    "cryptography==2.9.2" \
    "pyOpenSSL==19.1.0" \
    "cffi==1.14.6"
LABEL quirk.lab="image-old-pycrypto" \
      quirk.cryptography-version="2.9.2"
CMD ["python3", "-c", "import cryptography; print(cryptography.__version__); import time; time.sleep(9999)"]
