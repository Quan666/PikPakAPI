from typing import Any, Dict, List
import httpx
from .enums import DownloadStatus
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

    def get_headers(self, access_token: str = None) -> Dict[str, str]:
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
    ) -> Dict[str, Any]:
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
    ) -> Dict[str, Any]:
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

    async def login(self) -> None:
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

    async def refresh_access_token(self) -> None:
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

    def get_user_info(self) -> Dict[str, str]:
        """
        Get user info
        """
        return {
            "username": self.username,
            "user_id": self.user_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }

    async def offline_download(
        self, file_url: str, parent_id: str = None, name: str = None
    ) -> Dict[str, Any]:
        """
        file_url: str - 文件链接
        parent_id: str - 父文件夹id, 不传默认存储到 My Pack
        name: str - 文件名, 不传默认为文件链接的文件名

        离线下载磁力链
        """
        download_url = f"https://{self.PIKPAK_API_HOST}/drive/v1/files"
        download_data = {
            "kind": "drive#file",
            "name": name,
            "upload_type": "UPLOAD_TYPE_URL",
            "url": {"url": file_url},
            "folder_type": "DOWNLOAD" if not parent_id else "",
            "parent_id": parent_id,
        }
        result = await self._request_post(
            download_url, download_data, self.get_headers(), self.proxy
        )
        return result

    async def create_folder(
        self, name: str = "新建文件夹", parent_id: str = None
    ) -> Dict[str, Any]:
        """
        name: str - 文件夹名称
        parent_id: str - 父文件夹id, 默认创建到根目录
        创建文件夹
        """
        url = f"https://{self.PIKPAK_API_HOST}/drive/v1/files"
        data = {
            "kind": "drive#folder",
            "name": name,
            "parent_id": parent_id,
        }
        result = await self._request_post(url, data, self.get_headers(), self.proxy)
        return result

    async def delete_to_trash(self, ids: List[str]) -> Dict[str, Any]:
        """
        ids: List[str] - 文件夹、文件id列表
        将文件夹、文件移动到回收站
        """
        url = f"https://{self.PIKPAK_API_HOST}/drive/v1/files:batchTrash"
        data = {
            "ids": ids,
        }
        result = await self._request_post(url, data, self.get_headers(), self.proxy)
        return result

    async def untrash(self, ids: List[str]) -> Dict[str, Any]:
        """
        ids: List[str] - 文件夹、文件id列表
        将文件夹、文件移出回收站
        """
        url = f"https://{self.PIKPAK_API_HOST}/drive/v1/files:batchUntrash"
        data = {
            "ids": ids,
        }
        result = await self._request_post(url, data, self.get_headers(), self.proxy)
        return result

    async def delete_forever(self, ids: List[str]) -> Dict[str, Any]:
        """
        ids: List[str] - 文件夹、文件id列表
        永远删除文件夹、文件, 慎用
        """
        url = f"https://{self.PIKPAK_API_HOST}/drive/v1/files:batchDelete"
        data = {
            "ids": ids,
        }
        result = await self._request_post(url, data, self.get_headers(), self.proxy)
        return result

    async def offline_list(
        self, size: int = 10000, next_page_token: str = None
    ) -> Dict[str, Any]:
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

    async def offline_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        file_id: str - 离线下载文件id
        离线下载文件信息
        """
        url = f"https://{self.PIKPAK_API_HOST}/drive/v1/files/{file_id}"
        result = await self._request_get(
            url, {"thumbnail_size": "SIZE_LARGE"}, self.get_headers(), self.proxy
        )
        return result

    async def file_list(
        self, size: int = 100, parent_id: str = None, next_page_token: str = None
    ) -> Dict[str, Any]:
        """
        size: int - 每次请求的数量
        parent_id: str - 父文件夹id, 默认列出根目录
        next_page_token: str - 下一页的page token
        获取文件列表
        """
        list_url = f"https://{self.PIKPAK_API_HOST}/drive/v1/files"
        list_data = {
            "parent_id": parent_id,
            "thumbnail_size": "SIZE_MEDIUM",
            "limit": size,
            "with_audit": "true",
            "next_page_token": next_page_token,
            "filters": """{"trashed":{"eq":false},"phase":{"eq":"PHASE_TYPE_COMPLETE"}}""",
        }
        result = await self._request_get(
            list_url, list_data, self.get_headers(), self.proxy
        )
        return result

    async def events(
        self, size: int = 100, next_page_token: str = None
    ) -> Dict[str, Any]:
        """
        size: int - 每次请求的数量
        next_page_token: str - 下一页的page token

        获取最近添加事件列表
        """
        list_url = f"https://{self.PIKPAK_API_HOST}/drive/v1/events"
        list_data = {
            "thumbnail_size": "SIZE_MEDIUM",
            "limit": size,
            "next_page_token": next_page_token,
        }
        result = await self._request_get(
            list_url, list_data, self.get_headers(), self.proxy
        )
        return result

    async def offline_task_retry(self, task_id: str) -> Dict[str, Any]:
        """
        task_id: str - 离线下载任务id
        重试离线下载任务
        """
        list_url = f"https://{self.PIKPAK_API_HOST}/drive/v1/task"
        list_data = {
            "type": "offline",
            "create_type": "RETRY",
            "id": task_id,
        }
        try:
            result = await self._request_get(
                list_url, list_data, self.get_headers(), self.proxy
            )
            return result
        except Exception as e:
            raise PikpakException(f"重试离线下载任务失败: {task_id}")

    async def get_task_status(self, task_id: str, file_id: str) -> DownloadStatus:
        """
        task_id: str - 离线下载任务id
        file_id: str - 离线下载文件id
        获取离线下载任务状态, 临时实现, 后期可能变更
        """
        try:
            infos = await self.offline_list()
            if infos and infos.get("tasks", []):
                for task in infos.get("tasks", []):
                    if task_id == task.get("id"):
                        return DownloadStatus.downloading
            file_info = await self.offline_file_info(file_id=file_id)
            if file_info:
                return DownloadStatus.done
            else:
                return DownloadStatus.not_found
        except PikpakAccessTokenExpireException as e:
            await self.login()
            await self.get_task_status(task_id, file_id)
        except PikpakException as e:
            return DownloadStatus.error

    async def path_to_id(self, path: str, create: bool = False) -> List[str]:
        """
        path: str - 路径
        create: bool - 是否创建不存在的文件夹
        将形如 /path/a/b 的路径转换为 文件夹的id
        """
        if not path or len(path) <= 0:
            return None
        paths = path.split("/")
        paths = [p.strip() for p in paths if len(p) > 0]
        path_ids = []
        count = 0
        next_page_token = None
        parent_id = None
        while count < len(paths):
            data = await self.file_list(
                parent_id=parent_id, next_page_token=next_page_token
            )
            id = ""
            for f in data.get("files", []):
                if (
                    f.get("kind", "") == "drive#folder"
                    and f.get("name") == paths[count]
                ):
                    id = f.get("id")
                    break
            if id:
                path_ids.append(
                    {
                        "id": id,
                        "name": paths[count],
                    }
                )
                count += 1
                parent_id = id
            elif data.get("next_page_token"):
                next_page_token = data.get("next_page_token")
            elif create:
                data = await self.create_folder(name=paths[count], parent_id=parent_id)
                id = data.get("file").get("id")
                path_ids.append(
                    {
                        "id": id,
                        "name": paths[count],
                    }
                )
                count += 1
                parent_id = id
            else:
                break
        return path_ids
