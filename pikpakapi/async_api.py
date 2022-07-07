import httpx
from .PikpakException import PikpakException, PikpakAccessTokenExpireException


class PikPakApiAsync:
    """
    PikPakApiAsync class

    Attributes:
        CLIENT_ID: str - PikPak API client id
        CLIENT_SECRET: str - PikPak API client secret
        PIKPAK_API_HOST: str - PikPak API host
        PIKPAK_USER_HOST: str - PikPak user API host

        username: str - username of the user
        password: str - password of the user
        access_token: str - access token of the user , expire in 7200
        refresh_token: str - refresh token of the user
        proxy: str - proxy to use, e.g. "localhost:1080"
        user_id: str - user id of the user

    """

    PIKPAK_API_HOST = "api-drive.mypikpak.com"
    PIKPAK_USER_HOST = "user.mypikpak.com"

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

        self.access_token = None
        self.refresh_token = None

        self.proxy: httpx.Proxy = (
            httpx.Proxy(
                url=f"http://{proxy}",
            )
            if proxy
            else {}
        )

        self.user_id = None

    def get_headers(self, access_token: str = None):
        """
        Returns the headers to use for the requests.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36",
            "Content-Type": "application/json; charset=utf-8",
        }

        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"

        return headers

    async def _request_get(
        self,
        url: str,
        params: dict = None,
        headers: dict = None,
        proxies: httpx.Proxy = None,
    ):
        async with httpx.AsyncClient(proxies=proxies) as client:
            response = await client.get(url, params=params, headers=headers)
            json_data = response.json()
            if "error" in json_data:
                if json_data["error_code"] == 16:
                    raise PikpakAccessTokenExpireException(
                        json_data["error_description"]
                    )
                raise PikpakException(f"{json_data['error_description']}")
            return json_data

    async def _request_post(
        self,
        url: str,
        data: dict = None,
        headers: dict = None,
        proxies: httpx.Proxy = None,
    ):
        async with httpx.AsyncClient(proxies=proxies) as client:
            response = await client.post(url, json=data, headers=headers)
            json_data = response.json()
            if "error" in json_data:
                if json_data["error_code"] == 16:
                    raise PikpakAccessTokenExpireException(
                        json_data["error_description"]
                    )
                raise PikpakException(f"{json_data['error_description']}")
            return json_data

    async def login(self):
        """
        Login to PikPak
        """
        login_url = f"https://{PikPakApiAsync.PIKPAK_USER_HOST}/v1/auth/signin"
        login_data = {
            "client_id": self.CLIENT_ID,
            "client_secret": self.CLIENT_SECRET,
            "password": self.password,
            "username": self.username,
        }
        user_info = await self._request_post(
            login_url, login_data, self.get_headers(), self.proxy
        )
        self.access_token = user_info["access_token"]
        self.refresh_token = user_info["refresh_token"]
        self.user_id = user_info["sub"]

    async def refresh_access_token(self):
        """
        Refresh access token
        """
        refresh_url = f"https://{self.PIKPAK_USER_HOST}/v1/auth/token"
        refresh_data = {
            "client_id": self.CLIENT_ID,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        user_info = await self._request_post(
            refresh_url, refresh_data, self.get_headers(), self.proxy
        )
        self.access_token = user_info["access_token"]
        self.refresh_token = user_info["refresh_token"]
        self.user_id = user_info["sub"]

    def get_user_info(self):
        """
        Get user info
        """
        return {
            "username": self.username,
            "user_id": self.user_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }

    async def offline_download(self, file_url: str):
        """
        file_url: str - 文件链接
        离线下载磁力链
        """
        download_url = f"https://{self.PIKPAK_API_HOST}/drive/v1/files"
        download_data = {
            "kind": "drive#file",
            "name": "",
            "upload_type": "UPLOAD_TYPE_URL",
            "url": {"url": file_url},
            "folder_type": "DOWNLOAD",
        }
        result = await self._request_post(
            download_url, download_data, self.get_headers(), self.proxy
        )
        return result

    async def offline_list(
        self, size: int = 10000, next_page_token: str = None
    ) -> dict:
        """
        size: int - 每次请求的数量
        next_page_token: str - 下一页的page token
        获取离线下载列表
        """
        list_url = f"https://{self.PIKPAK_API_HOST}/drive/v1/tasks"
        list_data = {
            "type": "offline",
            "thumbnail_size": "SIZE_SMALL",
            "limit": size,
            "next_page_token": next_page_token,
            "filters": """{"phase": {"in": "PHASE_TYPE_RUNNING,PHASE_TYPE_ERROR"}}""",
        }
        result = await self._request_get(
            list_url, list_data, self.get_headers(), self.proxy
        )
        return result

    async def offline_file_info(self, file_id: str):
        """
        file_id: str - 离线下载文件id
        离线下载文件信息
        """
        url = f"https://{self.PIKPAK_API_HOST}/drive/v1/files/{file_id}"
        result = await self._request_get(
            url, {"thumbnail_size": "SIZE_LARGE"}, self.get_headers(), self.proxy
        )
        return result
