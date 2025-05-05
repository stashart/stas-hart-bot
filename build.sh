#!/bin/bash

# Установим ffmpeg
apt-get update && apt-get install -y ffmpeg

# Запуск приложения
python main.py
