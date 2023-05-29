name: Deploy to Raspberry Pi
on:
  push:
    branches:
      - main  # или замените на вашу основную ветку

jobs:
  deploy:
    runs-on: ubuntu-latest  # или выберите подходящий образ, совместимый с вашим Raspberry Pi

    steps:
    - name: Check out code
      uses: actions/checkout@v2

    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11.3  # замените на нужную версию Python

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt  # замените на ваш файл зависимостей

    - name: Update repository
      run: ssh master@185.155.17.223 'cd FlowergrammerBot && git pull'

    - name: Stop previous bot process
      run: ssh master@185.155.17.223 'pkill -f bot.py'

    - name: Start new bot process
      run: ssh master@185.155.17.223 'cd FlowergrammerBot && python bot.py'
