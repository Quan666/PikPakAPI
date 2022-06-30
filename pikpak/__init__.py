import requests


class PikPakAPI:

    PIKPAK_API_URL = "https://api-drive.mypikpak.com"
    PIKPAK_USER_URL = "https://user.mypikpak.com"

    CLIENT_ID = "YNxT9w7GMdWvEOKa"
    CLIENT_SECRET = "dbw2OtmVEeuUvIptb1Coygx"

    def __init__(self, username: str, password: str, proxy: str = None):
        """
        username: str - username of the user
        password: str - password of the user
        proxy: str - proxy to use, e.g. "localhost:1080"
        """

        self.username = username
        self.password = password
        self.proxy = {"http": proxy, "https": proxy} if proxy else None

        self.session = requests.Session()
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
            "Content-Type": "application/json; charset=utf-8",
            "Host": "user.mypikpak.com",
        }

        self.user_info = None
        self.login()

    def login(self):
        login_url = f"{PikPakAPI.PIKPAK_USER_URL}/v1/auth/signin"
        login_data = {
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "password": self.password,
            "username": self.username,
        }
        self.headers["Host"] = "user.mypikpak.com"

        response = self.session.post(
            login_url,
            json=login_data,
            headers=self.headers,
            proxies=self.proxy,
        )
        user_info = response.json()
        self.headers["Authorization"] = f"Bearer {user_info['access_token']}"
        self.headers["Host"] = "api-drive.mypikpak.com"
        self.user_info = user_info

    def get_user_info(self):
        return self.user_info

    def offline_download(self, file_url: str):
        """
        file_url: str - 文件链接
        离线下载磁力链
        """
        download_url = f"{self.PIKPAK_API_URL}/drive/v1/files"
        download_data = {
            "kind": "drive#file",
            "name": "",
            "upload_type": "UPLOAD_TYPE_URL",
            "url": {"url": file_url},
            "folder_type": "DOWNLOAD",
        }
        result = self.session.post(
            download_url,
            json=download_data,
            headers=self.headers,
            proxies=self.proxy,
        ).json()
        if "error" in result:
            if result["error_code"] == 16:
                self.login()
                return self.offline_download(file_url)
            raise Exception(f"出现错误：{result['error_description']}")
        return result

    def offline_list(self, size: int = 10000, next_page_token: str = None) -> dict:
        """
        size: int - 每次请求的数量
        next_page_token: str - 下一页的page token
        获取离线下载列表
        """
        list_url = f"{self.PIKPAK_API_URL}/drive/v1/tasks"
        list_data = {
            "type": "offline",
            "thumbnail_size": "SIZE_SMALL",
            "limit": size,
            "next_page_token": next_page_token,
            "filters": """{"phase": {"in": "PHASE_TYPE_RUNNING,PHASE_TYPE_ERROR"}}""",
        }
        result = self.session.get(
            list_url,
            params=list_data,
            headers=self.headers,
            proxies=self.proxy,
        ).json()
        if "error" in result:
            if result["error_code"] == 16:
                self.login()
                return self.offline_list()
            raise Exception(f"出现错误：{result['error_description']}")
        return result

    def offline_file_info(self, task_id: str):
        """
        task_id: str - 离线下载任务id
        离线下载文件信息
        """
        url = f"{self.PIKPAK_API_URL}/drive/v1/files/{task_id}"
        result = self.session.get(
            url,
            params={"thumbnail_size": "SIZE_LARGE"},
            headers=self.headers,
            proxies=self.proxy,
        ).json()
        if "error" in result:
            if result["error_code"] == 16:
                self.login()
                return self.offline_file_info(task_id)
            raise Exception(f"出现错误：{result['error_description']}")
        return result
