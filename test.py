import json
from pikpakapi import PikPakApi
import asyncio


async def test():
    client = PikPakApi(
        username="your_username",
        password="your_password",
        proxy="127.0.0.1:7890",
    )
    await client.login()
    print(json.dumps(client.get_user_info(), indent=4))
    print("=" * 30, end="\n\n")

    print(
        json.dumps(
            await client.offline_download(
                "magnet:?xt=urn:btih:42b46b971332e776e8b290ed34632d5c81a1c47c"
            ),
            indent=4,
        )
    )
    print("=" * 30, end="\n\n")

    print(json.dumps(await client.offline_list(), indent=4))
    print("=" * 30, end="\n\n")

    print(
        json.dumps(
            await client.offline_file_info("VN5omQUMRn5NlHL8lMt91q5Io1"), indent=4
        )
    )
    print("=" * 30, end="\n\n")

    print(
        json.dumps(
            await client.file_rename("VNayNjZtsdmka4YrwZWVj-r4o1", '[Nekomoe kissaten][Deaimon][11][1080p][CHS]_01.mp4'), indent=4
        )
    )
    print("=" * 30, end="\n\n")

    print(
        json.dumps(
            await client.file_batch_star(ids=['VN6qSS-FBcaI6l7YltWsjUU1o1']), indent=4
        )
    )
    print("=" * 30, end="\n\n")

    print(
        json.dumps(
            await client.file_batch_unstar(ids=['VN6qSS-FBcaI6l7YltWsjUU1o1']), indent=4
        )
    )
    print("=" * 30, end="\n\n")

    print(
        json.dumps(
            await client.file_star_list(), indent=4
        )
    )
    print("=" * 30, end="\n\n")

    print(
        json.dumps(
            await client.file_batch_share(ids=['VN6qSS-FBcaI6l7YltWsjUU1o1'], need_password=True)
        )
    )
    print("=" * 30, end="\n\n")

    print(
        json.dumps(
            await client.get_quota_info(), indent=4
        )
    )
    print("=" * 30, end="\n\n")

if __name__ == "__main__":
    asyncio.run(test())
