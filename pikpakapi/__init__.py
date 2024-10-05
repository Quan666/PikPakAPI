import asyncio
import binascii
import json
import logging
import re
from base64 import b64decode, b64encode
from hashlib import md5
from typing import Any, Dict, List, Optional, Literal

import httpx

from .PikpakException import PikpakException, PikpakRetryException
from .enums import DownloadStatus
from .utils import (
    PIKPAK_CLIENT_ID,
    CLIENT_SECRET,
    CLIENT_VERSION,
    PACKAG_ENAME,
    build_custom_user_agent,
    captcha_sign,
    get_timestamp,
    FILEPAX_CLIENT_ID,
)


class PikPakApi:
    """
    PikPakApi class

    Attributes:
        PIKPAK_API_HOST: str - PikPak API host
        PIKPAK_USER_HOST: str - PikPak user API host
        FILEPAX_API_HOST: str - FilePax API host
        FILEPAX_USER_HOST: str - FilePax user API host

        username: str - username of the user
        password: str - password of the user
        encoded_token: str - encoded token of the user with access and refresh tokens
        access_token: str - access token of the user , expire in 7200
        refresh_token: str - refresh token of the user
        user_id: str - user id of the user

    """

    PIKPAK_API_HOST = "api-drive.mypikpak.com"
    PIKPAK_USER_HOST = "user.mypikpak.com"
    FILEPAX_API_HOST = "api-drive.filepax.com"
    FILEPAX_USER_HOST = "user.filepax.com"

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        encoded_token: Optional[str] = None,
        httpx_client_args: Optional[Dict[str, Any]] = None,
        device_id: Optional[str] = None,
        request_max_retries: int = 3,
        request_initial_backoff: float = 3.0,
        host: Literal["pikpak", "filepax"] = "pikpak",
    ):
        """
        username: str - username of the user
        password: str - password of the user
        encoded_token: str - encoded token of the user with access and refresh token
        httpx_client_args: dict - extra arguments for httpx.AsyncClient (https://www.python-httpx.org/api/#asyncclient)
        device_id: str - device id to identify the device
        request_max_retries: int - maximum number of retries for requests
        request_initial_backoff: float - initial backoff time for retries
        host: str - host to use, pikpak or filepax
        """

        self.username = username
        self.password = password
        self.encoded_token = encoded_token
        self.max_retries = request_max_retries
        self.initial_backoff = request_initial_backoff
        self.host = host
        self.api_host = (
            self.PIKPAK_API_HOST if host == "pikpak" else self.FILEPAX_API_HOST
        )
        self.user_host = (
            self.PIKPAK_USER_HOST if host == "pikpak" else self.FILEPAX_USER_HOST
        )

        self.access_token = None
        self.refresh_token = None
        self.user_id = None

        # device_id is used to identify the device, if not provided, a random device_id will be generated, 32 characters
        self.device_id = (
            device_id
            if device_id
            else md5(f"{self.username}{self.password}".encode()).hexdigest()
        )
        self.captcha_token = None

        httpx_client_args = httpx_client_args or {"timeout": 10}
        self.httpx_client = httpx.AsyncClient(**httpx_client_args)

        self._path_id_cache: Dict[str, Any] = {}

        self.user_agent: Optional[str] = None

        if self.encoded_token:
            self.decode_token()
        elif self.username and self.password:
            pass
        else:
            raise PikpakException("username and password or encoded_token is required")

    def build_custom_user_agent(self) -> str:

        self.user_agent = build_custom_user_agent(
            device_id=self.device_id,
            user_id=self.user_id if self.user_id else "",
        )
        return self.user_agent

    def get_headers(self, access_token: Optional[str] = None) -> Dict[str, str]:
        """
        Returns the headers to use for the requests.
        """
        headers = {
            "User-Agent": (
                self.build_custom_user_agent()
                if self.captcha_token
                else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
            "Content-Type": "application/json; charset=utf-8",
        }

        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        if self.captcha_token:
            headers["X-Captcha-Token"] = self.captcha_token
        if self.device_id:
            headers["X-Device-Id"] = self.device_id
        return headers

    async def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = await self._send_request(method, url, data, params, headers)
                return await self._handle_response(response)
            except PikpakRetryException as error:
                logging.info(f"Retry attempt {attempt + 1}/{self.max_retries}")
                last_error = error
            except PikpakException:
                raise
            except httpx.HTTPError as error:
                logging.error(
                    f"HTTP Error on attempt {attempt + 1}/{self.max_retries}: {str(error)}"
                )
                last_error = error
            except Exception as error:
                logging.error(
                    f"Unexpected error on attempt {attempt + 1}/{self.max_retries}: {str(error)}"
                )
                last_error = error

            await asyncio.sleep(self.initial_backoff * (2**attempt))

        # If we've exhausted all retries, raise an exception with the last error
        raise PikpakException(f"Max retries reached. Last error: {str(last_error)}")

    async def _send_request(self, method, url, data, params, headers):
        req_headers = headers or self.get_headers()
        return await self.httpx_client.request(
            method,
            url,
            json=data,
            params=params,
            headers=req_headers,
        )

    async def _handle_response(self, response) -> Dict[str, Any]:
        try:
            json_data = response.json()
        except ValueError:
            if response.status_code == 200:
                return {}
            raise PikpakRetryException("Empty JSON data")

        if not json_data:
            if response.status_code == 200:
                return {}
            raise PikpakRetryException("Empty JSON data")

        if "error" not in json_data:
            return json_data

        if json_data["error"] == "invalid_account_or_password":
            raise PikpakException("Invalid username or password")

        if json_data.get("error_code") == 16:
            await self.refresh_access_token()
            raise PikpakRetryException("Token refreshed, please retry")

        raise PikpakException(json_data.get("error_description", "Unknown Error"))

    async def _request_get(
        self,
        url: str,
        params: dict = None,
    ):
        return await self._make_request("get", url, params=params)

    async def _request_post(
        self,
        url: str,
        data: dict = None,
        headers: dict = None,
    ):
        return await self._make_request("post", url, data=data, headers=headers)

    async def _request_patch(
        self,
        url: str,
        data: dict = None,
    ):
        return await self._make_request("patch", url, data=data)

    async def _request_delete(
        self,
        url: str,
        params: dict = None,
        data: dict = None,
    ):
        return await self._make_request("delete", url, params=params, data=data)

    def decode_token(self):
        """Decodes the encoded token to update access and refresh tokens."""
        try:
            decoded_data = json.loads(b64decode(self.encoded_token).decode())
        except (binascii.Error, json.JSONDecodeError):
            raise PikpakException("Invalid encoded token")
        if not decoded_data.get("access_token") or not decoded_data.get(
            "refresh_token"
        ):
            raise PikpakException("Invalid encoded token")
        self.access_token = decoded_data.get("access_token")
        self.refresh_token = decoded_data.get("refresh_token")

    def encode_token(self):
        """Encodes the access and refresh tokens into a single string."""
        token_data = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
        }
        self.encoded_token = b64encode(json.dumps(token_data).encode()).decode()

    async def captcha_init(self, action: str, meta: dict = None) -> Dict[str, Any]:
        url = f"https://{self.user_host}/v1/shield/captcha/init"
        if not meta:
            t = f"{get_timestamp()}"
            meta = {
                "captcha_sign": captcha_sign(self.device_id, t),
                "client_version": CLIENT_VERSION,
                "package_name": PACKAG_ENAME,
                "user_id": self.user_id,
                "timestamp": t,
            }
        params = {
            "client_id": (
                PIKPAK_CLIENT_ID if self.host == "pikpak" else FILEPAX_CLIENT_ID
            ),
            "action": action,
            "device_id": self.device_id,
            "meta": meta,
        }
        return await self._request_post(url, data=params)

    async def login(self) -> None:
        """
        Login to PikPak
        """
        login_path = "/v1/auth/signin"
        login_url = f"https://{self.user_host}{login_path}"
        metas = {}
        if not self.username or not self.password:
            raise PikpakException("username and password are required")
        if re.match(r"\w+([-+.]\w+)*@\w+([-.]\w+)*\.\w+([-.]\w+)*", self.username):
            metas["email"] = self.username
        elif re.match(r"\d{11,18}", self.username):
            metas["phone_number"] = self.username
        else:
            metas["username"] = self.username
        result = await self.captcha_init(
            action=f"POST:{login_url if self.host == 'pikpak' else login_path}",
            meta=metas,
        )
        captcha_token = result.get("captcha_token", "")
        if not captcha_token:
            raise PikpakException("captcha_token get failed")
        if self.host == "pikpak":
            login_data = {
                "client_id": PIKPAK_CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "password": self.password,
                "username": self.username,
                "captcha_token": captcha_token,
            }
            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }
        else:
            login_data = {
                "client_id": FILEPAX_CLIENT_ID,
                "password": self.password,
                "username": self.username,
            }
            headers = {
                "Content-Type": "application/json",
            }
        user_info = await self._request_post(
            login_url,
            login_data,
            headers,
        )
        self.access_token = user_info["access_token"]
        self.refresh_token = user_info["refresh_token"]
        self.user_id = user_info["sub"]
        self.encode_token()

    async def refresh_access_token(self) -> None:
        """
        Refresh access token
        """
        refresh_url = f"https://{self.user_host}/v1/auth/token"
        refresh_data = {
            "client_id": (
                PIKPAK_CLIENT_ID if self.host == "pikpak" else FILEPAX_CLIENT_ID
            ),
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        user_info = await self._request_post(refresh_url, refresh_data)
        self.access_token = user_info["access_token"]
        self.refresh_token = user_info["refresh_token"]
        self.user_id = user_info["sub"]
        self.encode_token()

    def get_user_info(self) -> Dict[str, Optional[str]]:
        """
        Get user info
        """
        return {
            "username": self.username,
            "user_id": self.user_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "encoded_token": self.encoded_token,
        }

    async def create_folder(
        self, name: str = "新建文件夹", parent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        name: str - 文件夹名称
        parent_id: str - 父文件夹id, 默认创建到根目录

        创建文件夹
        """
        url = f"https://{self.api_host}/drive/v1/files"
        data = {
            "kind": "drive#folder",
            "name": name,
            "parent_id": parent_id,
        }
        result = await self._request_post(url, data)
        return result

    async def delete_to_trash(self, ids: List[str]) -> Dict[str, Any]:
        """
        ids: List[str] - 文件夹、文件id列表

        将文件夹、文件移动到回收站
        """
        url = f"https://{self.api_host}/drive/v1/files:batchTrash"
        data = {
            "ids": ids,
        }
        result = await self._request_post(url, data)
        return result

    async def untrash(self, ids: List[str]) -> Dict[str, Any]:
        """
        ids: List[str] - 文件夹、文件id列表

        将文件夹、文件移出回收站
        """
        url = f"https://{self.api_host}/drive/v1/files:batchUntrash"
        data = {
            "ids": ids,
        }
        result = await self._request_post(url, data)
        return result

    async def delete_forever(self, ids: List[str]) -> Dict[str, Any]:
        """
        ids: List[str] - 文件夹、文件id列表

        永远删除文件夹、文件, 慎用
        """
        url = f"https://{self.api_host}/drive/v1/files:batchDelete"
        data = {
            "ids": ids,
        }
        result = await self._request_post(url, data)
        return result

    async def offline_download(
        self, file_url: str, parent_id: Optional[str] = None, name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        file_url: str - 文件链接
        parent_id: str - 父文件夹id, 不传默认存储到 My Pack
        name: str - 文件名, 不传默认为文件链接的文件名

        离线下载磁力链
        """
        download_url = f"https://{self.api_host}/drive/v1/files"
        download_data = {
            "kind": "drive#file",
            "name": name,
            "upload_type": "UPLOAD_TYPE_URL",
            "url": {"url": file_url},
            "folder_type": "DOWNLOAD" if not parent_id else "",
            "parent_id": parent_id,
        }
        result = await self._request_post(download_url, download_data)
        return result

    async def offline_list(
        self,
        size: int = 10000,
        next_page_token: Optional[str] = None,
        phase: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        size: int - 每次请求的数量
        next_page_token: str - 下一页的page token
        phase: List[str] - Offline download task status, default is ["PHASE_TYPE_RUNNING", "PHASE_TYPE_ERROR"]
            supported values: PHASE_TYPE_RUNNING, PHASE_TYPE_ERROR, PHASE_TYPE_COMPLETE, PHASE_TYPE_PENDING

        获取离线下载列表
        """
        if phase is None:
            phase = ["PHASE_TYPE_RUNNING", "PHASE_TYPE_ERROR"]
        list_url = f"https://{self.api_host}/drive/v1/tasks"
        list_data = {
            "type": "offline",
            "thumbnail_size": "SIZE_SMALL",
            "limit": size,
            "page_token": next_page_token,
            "filters": json.dumps({"phase": {"in": ",".join(phase)}}),
            "with": "reference_resource",
        }
        result = await self._request_get(list_url, list_data)
        return result

    async def offline_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        file_id: str - 离线下载文件id

        离线下载文件信息
        """
        url = f"https://{self.api_host}/drive/v1/files/{file_id}"
        result = await self._request_get(url, {"thumbnail_size": "SIZE_LARGE"})
        return result

    async def file_list(
        self,
        size: int = 100,
        parent_id: Optional[str] = None,
        next_page_token: Optional[str] = None,
        additional_filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        size: int - 每次请求的数量
        parent_id: str - 父文件夹id, 默认列出根目录
        next_page_token: str - 下一页的page token
        additional_filters: Dict[str, Any] - 额外的过滤条件

        获取文件列表，可以获得文件下载链接
        """
        default_filters = {
            "trashed": {"eq": False},
            "phase": {"eq": "PHASE_TYPE_COMPLETE"},
        }
        if additional_filters:
            default_filters.update(additional_filters)
        list_url = f"https://{self.api_host}/drive/v1/files"
        list_data = {
            "parent_id": parent_id,
            "thumbnail_size": "SIZE_MEDIUM",
            "limit": size,
            "with_audit": "true",
            "page_token": next_page_token,
            "filters": json.dumps(default_filters),
        }
        # FixME
        response = await self.captcha_init(
            action="GET:/drive/v1/files",
        )
        self.captcha_token = response.get("captcha_token")
        result = await self._request_get(list_url, list_data)
        self.captcha_token = None
        return result

    async def events(
        self, size: int = 100, next_page_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        size: int - 每次请求的数量
        next_page_token: str - 下一页的page token

        获取最近添加事件列表
        """
        list_url = f"https://{self.api_host}/drive/v1/events"
        list_data = {
            "thumbnail_size": "SIZE_MEDIUM",
            "limit": size,
            "next_page_token": next_page_token,
        }
        result = await self._request_get(list_url, list_data)
        return result

    async def offline_task_retry(self, task_id: str) -> Dict[str, Any]:
        """
        task_id: str - 离线下载任务id

        重试离线下载任务
        """
        list_url = f"https://{self.api_host}/drive/v1/task"
        list_data = {
            "type": "offline",
            "create_type": "RETRY",
            "id": task_id,
        }
        try:
            result = await self._request_post(list_url, list_data)
            return result
        except Exception as e:
            raise PikpakException(f"重试离线下载任务失败: {task_id}. {e}")

    async def delete_tasks(
        self, task_ids: List[str], delete_files: bool = False
    ) -> None:
        """
        delete tasks by task ids
        task_ids: List[str] - task ids to delete
        """
        delete_url = f"https://{self.api_host}/drive/v1/tasks"
        params = {
            "task_ids": task_ids,
            "delete_files": delete_files,
        }
        try:
            await self._request_delete(delete_url, params=params)
        except Exception as e:
            raise PikpakException(f"Failing to delete tasks: {task_ids}. {e}")

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
        except PikpakException:
            return DownloadStatus.error

    async def path_to_id(self, path: str, create: bool = False) -> List[Dict[str, str]]:
        """
        path: str - 路径
        create: bool - 是否创建不存在的文件夹

        将形如 /path/a/b 的路径转换为 文件夹的id
        """
        if not path or len(path) <= 0:
            return []
        paths = path.split("/")
        paths = [p.strip() for p in paths if len(p) > 0]
        # 构造不同级别的path表达式，尝试找到距离目标最近的那一层
        multi_level_paths = ["/" + "/".join(paths[: i + 1]) for i in range(len(paths))]
        path_ids = [
            self._path_id_cache[p]
            for p in multi_level_paths
            if p in self._path_id_cache
        ]
        # 判断缓存命中情况
        hit_cnt = len(path_ids)
        if hit_cnt == len(paths):
            return path_ids
        elif hit_cnt == 0:
            count = 0
            parent_id = None
        else:
            count = hit_cnt
            parent_id = path_ids[-1]["id"]

        next_page_token = None
        while count < len(paths):
            data = await self.file_list(
                parent_id=parent_id, next_page_token=next_page_token
            )
            record_of_target_path = None
            for f in data.get("files", []):
                current_path = "/" + "/".join(paths[:count] + [f.get("name")])
                file_type = (
                    "folder" if f.get("kind", "").find("folder") != -1 else "file"
                )
                record = {
                    "id": f.get("id"),
                    "name": f.get("name"),
                    "file_type": file_type,
                }
                self._path_id_cache[current_path] = record
                if f.get("name") == paths[count]:
                    record_of_target_path = record
                    # 不break: 剩下的文件也同样缓存起来
            if record_of_target_path is not None:
                path_ids.append(record_of_target_path)
                count += 1
                parent_id = record_of_target_path["id"]
            elif data.get("next_page_token") and (
                not next_page_token or next_page_token != data.get("next_page_token")
            ):
                next_page_token = data.get("next_page_token")
            elif create:
                data = await self.create_folder(name=paths[count], parent_id=parent_id)
                file_id = data.get("file").get("id")
                record = {
                    "id": file_id,
                    "name": paths[count],
                    "file_type": "folder",
                }
                path_ids.append(record)
                current_path = "/" + "/".join(paths[: count + 1])
                self._path_id_cache[current_path] = record
                count += 1
                parent_id = file_id
            else:
                break
        return path_ids

    async def file_batch_move(
        self,
        ids: List[str],
        to_parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        ids: List[str] - 文件id列表
        to_parent_id: str - 移动到的文件夹id, 默认为根目录

        批量移动文件
        """
        to = (
            {
                "parent_id": to_parent_id,
            }
            if to_parent_id
            else {}
        )
        result = await self._request_post(
            url=f"https://{self.api_host}/drive/v1/files:batchMove",
            data={
                "ids": ids,
                "to": to,
            },
        )
        return result

    async def file_batch_copy(
        self,
        ids: List[str],
        to_parent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        ids: List[str] - 文件id列表
        to_parent_id: str - 复制到的文件夹id, 默认为根目录

        批量复制文件
        """
        to = (
            {
                "parent_id": to_parent_id,
            }
            if to_parent_id
            else {}
        )
        result = await self._request_post(
            url=f"https://{self.api_host}/drive/v1/files:batchCopy",
            data={
                "ids": ids,
                "to": to,
            },
        )
        return result

    async def file_move_or_copy_by_path(
        self,
        from_path: List[str],
        to_path: str,
        move: bool = False,
        create: bool = False,
    ) -> Dict[str, Any]:
        """
        from_path: List[str] - 要移动或复制的文件路径列表
        to_path: str - 移动或复制到的路径
        is_move: bool - 是否移动, 默认为复制
        create: bool - 是否创建不存在的文件夹

        根据路径移动或复制文件
        """
        from_ids: List[str] = []
        for path in from_path:
            if path_ids := await self.path_to_id(path):
                if file_id := path_ids[-1].get("id"):
                    from_ids.append(file_id)
        if not from_ids:
            raise PikpakException("要移动的文件不存在")
        to_path_ids = await self.path_to_id(to_path, create=create)
        if to_path_ids:
            to_parent_id = to_path_ids[-1].get("id")
        else:
            to_parent_id = None
        if move:
            result = await self.file_batch_move(ids=from_ids, to_parent_id=to_parent_id)
        else:
            result = await self.file_batch_copy(ids=from_ids, to_parent_id=to_parent_id)
        return result

    async def get_download_url(self, file_id: str) -> Dict[str, Any]:
        """
        id: str - 文件id

        Returns the file details data.
        1. Use `medias[0][link][url]` for streaming with high speed in streaming services or tools.
        2. Use `web_content_link` to download the file
        """
        result = await self.captcha_init(
            action=f"GET:/drive/v1/files/{file_id}",
        )
        self.captcha_token = result.get("captcha_token")
        result = await self._request_get(
            url=f"https://{self.api_host}/drive/v1/files/{file_id}?",
        )
        self.captcha_token = None
        return result

    async def file_rename(self, id: str, new_file_name: str) -> Dict[str, Any]:
        """
        id: str - 文件id
        new_file_name: str - 新的文件名

        重命名文件
        返回文件的详细信息
        """
        data = {
            "name": new_file_name,
        }
        result = await self._request_patch(
            url=f"https://{self.api_host}/drive/v1/files/{id}",
            data=data,
        )
        return result

    async def file_batch_star(
        self,
        ids: List[str],
    ) -> Dict[str, Any]:
        """
        ids: List[str] - 文件id列表

        批量给文件加星标
        """
        data = {
            "ids": ids,
        }
        result = await self._request_post(
            url=f"https://{self.api_host}/drive/v1/files:star",
            data=data,
        )
        return result

    async def file_batch_unstar(
        self,
        ids: List[str],
    ) -> Dict[str, Any]:
        """
        ids: List[str] - 文件id列表

        批量给文件取消星标
        """
        data = {
            "ids": ids,
        }
        result = await self._request_post(
            url=f"https://{self.api_host}/drive/v1/files:unstar",
            data=data,
        )
        return result

    async def file_star_list(
        self,
        size: int = 100,
        next_page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        size: int - 每次请求的数量
        next_page_token: str - 下一页的page token

        获取加星标的文件列表，可以获得文件下载链接
        parent_id只可取默认值*，子目录列表通过获取星标目录以后自行使用file_list方法获取
        """
        additional_filters = {"system_tag": {"in": "STAR"}}
        result = await self.file_list(
            size=size,
            parent_id="*",
            next_page_token=next_page_token,
            additional_filters=additional_filters,
        )
        return result

    async def file_batch_share(
        self,
        ids: List[str],
        need_password: Optional[bool] = False,
        expiration_days: Optional[int] = -1,
    ) -> Dict[str, Any]:
        """
        ids: List[str] - 文件id列表
        need_password: Optional[bool] - 是否需要分享密码
        expiration_days: Optional[int] - 分享天数

        批量分享文件，并生成分享链接
        返回数据结构：
        {
            "share_id": "xxx", //分享ID
            "share_url": "https://mypikpak.com/s/xxx", // 分享链接
            "pass_code": "53fe", // 分享密码
            "share_text": "https://mypikpak.com/s/xxx",
            "share_list": []
        }
        """
        data = {
            "file_ids": ids,
            "share_to": "encryptedlink" if need_password else "publiclink",
            "expiration_days": expiration_days,
            "pass_code_option": "REQUIRED" if need_password else "NOT_REQUIRED",
        }
        result = await self._request_post(
            url=f"https://{self.api_host}/drive/v1/share",
            data=data,
        )
        return result

    async def get_quota_info(self) -> Dict[str, Any]:
        """
        获取当前空间的quota信息
        返回数据结构如下：
        {
            "kind": "drive#about",
            "quota": {
                "kind": "drive#quota",
                "limit": "10995116277760", //空间总大小， 单位Byte
                "usage": "5113157556024", // 已用空间大小，单位Byte
                "usage_in_trash": "1281564700871", // 回收站占用大小，单位Byte
                "play_times_limit": "-1",
                "play_times_usage": "0"
            },
            "expires_at": "",
            "quotas": {}
        }
        """
        result = await self._request_get(
            url=f"https://{self.api_host}/drive/v1/about",
        )
        return result

    async def get_invite_code(self):
        result = await self._request_get(
            url=f"https://{self.api_host}/vip/v1/activity/inviteCode",
        )
        return result["code"]

    async def vip_info(self):
        result = await self._request_get(
            url=f"https://{self.api_host}/drive/v1/privilege/vip",
        )
        return result

    async def get_transfer_quota(self) -> Dict[str, Any]:
        """
        Get transfer quota
        """
        url = f"https://{self.api_host}/vip/v1/quantity/list?type=transfer"
        result = await self._request_get(url)
        return result

    async def get_share_folder(
        self, share_id: str, pass_code_token: str, parent_id: str = None
    ) -> Dict[str, Any]:
        """
        获取分享链接下文件夹内容

        Args:
            share_id: str - 分享ID eg. /s/VO8BcRb-XXXXX 的 VO8BcRb-XXXXX
            pass_code_token: str - 通过 get_share_info 获取到的 pass_code_token
            parent_id: str - 父文件夹id, 默认列出根目录
        """
        data = {
            "limit": "100",
            "thumbnail_size": "SIZE_LARGE",
            "order": "6",
            "share_id": share_id,
            "parent_id": parent_id,
            "pass_code_token": pass_code_token,
        }
        url = f"https://{self.api_host}/drive/v1/share/detail"
        return await self._request_get(url, params=data)

    async def get_share_info(
        self, share_link: str, pass_code: str = None
    ) -> ValueError | Dict[str, Any] | List[Dict[str | Any, str | Any]]:
        """
        获取分享链接下内容

        Args:
            share_link: str - 分享链接
            pass_code: str - 分享密码, 无密码则留空
        """
        match = re.search(r"/s/([^/]+)(?:.*/([^/]+))?$", share_link)
        if match:
            share_id = match.group(1)
            parent_id = match.group(2) if match.group(2) else None
        else:
            return ValueError("Share Link Is Not Right")

        data = {
            "limit": "100",
            "thumbnail_size": "SIZE_LARGE",
            "order": "3",
            "share_id": share_id,
            "parent_id": parent_id,
            "pass_code": pass_code,
        }
        url = f"https://{self.api_host}/drive/v1/share"
        return await self._request_get(url, params=data)

    async def restore(
        self, share_id: str, pass_code_token: str, file_ids: List[str]
    ) -> Dict[str, Any]:
        """

        Args:
            share_id: 分享链接eg. /s/VO8BcRb-XXXXX 的 VO8BcRb-XXXXX
            pass_code_token: get_share_info获取, 无密码则留空
            file_ids: 需要转存的文件/文件夹ID列表, get_share_info获取id值
        """
        data = {
            "share_id": share_id,
            "pass_code_token": pass_code_token,
            "file_ids": file_ids,
        }
        result = await self._request_post(
            url=f"https://{self.api_host}/drive/v1/share/restore", data=data
        )
        return result
