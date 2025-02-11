# PikPakApi

PikPak API Python 实现

## Install

```sh
pip3 install pikpakapi
```

## Usage

```python
client = PikPakApi(
    username="your_username",
    password="your_password",
)
await client.login()
await client.refresh_access_token()
await client.offline_list()
```

## Features

- Login and refresh token
- Offline download task management
- File renaming, favoriting, sharing, and other operations

For more detailed information, please refer to the `test.py` file in the source code.
