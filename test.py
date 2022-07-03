import json
from pikpak import PikPakAPI

if __name__ == "__main__":

    client = PikPakAPI(
        username="your_username",
        password="your_password",
        proxy="127.0.0.1:7890",
    )
    client.login()
    print(json.dumps(client.get_user_info(), indent=4))
    print("=" * 30, end="\n\n")

    print(
        json.dumps(
            client.offline_download(
                "magnet:?xt=urn:btih:42b46b971332e776e8b290ed34632d5c81a1c47c"
            ),
            indent=4,
        )
    )
    print("=" * 30, end="\n\n")

    print(json.dumps(client.offline_list(), indent=4))
    print("=" * 30, end="\n\n")

    print(json.dumps(client.offline_file_info("VN5omQUMRn5NlHL8lMt91q5Io1"), indent=4))
