TO RUN LOCAL HOST:
ngrok http 5000
python sinch_messenger.py
python -m unittest discover -s tests -p "test_*.py"