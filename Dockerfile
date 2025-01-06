FROM python:3.8

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install libgl1-mesa-glx -y

RUN pip install -r requirements.txt

EXPOSE 5001

VOLUME /app/strm

CMD ["python", "FrameCapture.py"]