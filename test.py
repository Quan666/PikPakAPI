import asyncio
import json
import logging

import httpx

from pikpakapi import PikPakApi


async def test():
    client = PikPakApi(
        username="mhdzumair@gmail.com", password="Zumair@786", host="pikpak"
    )
    await client.login()
    await client.refresh_access_token()
    tasks = await client.offline_list()
    print(json.dumps(tasks, indent=4))
    print("=" * 30, end="\n\n")
    if tasks.get("tasks"):
        await client.delete_tasks(task_ids=[tasks["tasks"][0]["id"]])
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
            await client.file_rename(
                "VNayNjZtsdmka4YrwZWVj-r4o1",
                "[Nekomoe kissaten][Deaimon][11][1080p][CHS]_01.mp4",
            ),
            indent=4,
        )
    )
    print("=" * 30, end="\n\n")

    print(
        json.dumps(
            await client.file_batch_star(ids=["VN6qSS-FBcaI6l7YltWsjUU1o1"]), indent=4
        )
    )
    print("=" * 30, end="\n\n")

    print(
        json.dumps(
            await client.file_batch_unstar(ids=["VN6qSS-FBcaI6l7YltWsjUU1o1"]), indent=4
        )
    )
    print("=" * 30, end="\n\n")

    print(json.dumps(await client.file_star_list(), indent=4))
    print("=" * 30, end="\n\n")

    print(
        json.dumps(
            await client.file_batch_share(
                ids=["VN6qSS-FBcaI6l7YltWsjUU1o1"], need_password=True
            )
        )
    )
    print("=" * 30, end="\n\n")

    print(json.dumps(await client.get_quota_info(), indent=4))
    print("=" * 30, end="\n\n")

    print(
        json.dumps(
            await client.get_share_info(
                "https://mypikpak.com/s/VO8BcRb-0fibD0Ncymp8nxSMo1"
            ),
            indent=4,
        )
    )

    test_restore = await client.get_share_info(
        "https://mypikpak.com/s/VO8BcRb-0fibD0Ncymp8nxSMo1/VO8Ba45l-FRcCf559uZjwjFjo1"
    )

    await client.restore(
        share_id="VO8BcRb-0fibD0Ncymp8nxSMo1",
        pass_code_token=test_restore.get("pass_code_token"),
        file_ids=[
            "VO8BcNTLpxHtBHDFH0d5cGRzo1",
        ],
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )
    asyncio.run(test())
