# vidnavigator-python
Python SDK for the VidNavigator Developer API

## Installation

```bash
pip install vidnavigator  # or publish on PyPI
```

## Quickstart

```python
from vidnavigator import VidNavigatorClient

client = VidNavigatorClient(api_key="YOUR_API_KEY")

# Health check
print(client.health_check())

# Fetch transcript from YouTube
resp = client.get_transcript(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ"
)

# Get data as dictionary
data = resp.data.model_dump()
print(data)


## More Examples & Documentation

For a comprehensive set of usage examples covering all SDK features, please see the [`test.py`](test.py) file in this repository.

For full API documentation, visit [docs.vidnavigator.com](https://docs.vidnavigator.com).


## License

This SDK is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.
